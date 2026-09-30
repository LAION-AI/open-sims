from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from living_world.generation.catalog import CATALOG, ROOMS
from living_world.server import create_app
from living_world.workshop.library import Library
from living_world.workshop.providers import ApiProvider, DemoProvider, ProviderConfig, ProviderError
from living_world.workshop.runner import Runner, RunLimits, authoring_prompt
from living_world.workshop.schema import ContentPack


class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.library = Library(":memory:")
        self.addCleanup(self.library.close)

    def draft(self, jid="job_test"):
        return DemoProvider().complete(authoring_prompt(jid, "reading", self.library.inventory()), ContentPack.model_json_schema())[0]

    def test_data_pack_is_staged_tested_reviewed_and_reused_without_global_mutation(self):
        before = deepcopy((CATALOG, ROOMS))
        result = Runner(self.library, DemoProvider()).run(["Leseplätze ergänzen"])
        job = result["jobs"][0]
        self.assertEqual(job["state"], "awaiting_review")
        self.assertEqual(result["calls"], 2)
        self.assertEqual(job["report"]["room_checks"], 16)
        self.assertEqual(len(self.library.inventory()["publications"]), 0)
        with self.assertRaises(ValueError):
            self.library.publish(job["id"], "Tester")
        published = self.library.publish(job["id"], "Tester", visual_reviewed=True)
        self.assertEqual(published["state"], "published")
        snap = self.library.snapshot()
        self.assertIn(job["pack"]["objects"][0]["id"], snap["objects"])
        self.assertEqual((CATALOG, ROOMS), before)
        with self.assertRaises(ValueError):
            self.library.stage(job["id"], job["pack"])

    def test_budget_is_reserved_across_parallel_workers(self):
        result = Runner(self.library, DemoProvider(), RunLimits(3, 3, 3)).run(["Reading one", "Reading two", "Reading three"])
        self.assertEqual(result["calls"], 3)
        self.assertTrue(any(j["state"] == "failed" for j in result["jobs"]))
        self.assertEqual(self.library.inventory()["publications"], [])

    def test_three_workers_really_overlap_without_using_an_api(self):
        barrier, lock = threading.Barrier(3), threading.Lock()
        class ParallelFixture(DemoProvider):
            active = peak = 0
            def complete(inner, prompt, schema):
                with lock:
                    inner.active += 1
                    inner.peak = max(inner.peak, inner.active)
                barrier.wait(timeout=5)
                result = super().complete(prompt,schema)
                with lock:
                    inner.active -= 1
                return result
        provider = ParallelFixture()
        result = Runner(self.library,provider,RunLimits(3,3,6)).run(['Leseplatz A','Leseplatz B','Leseplatz C'])
        self.assertEqual(provider.peak,3)
        self.assertEqual(result['calls'],6)
        self.assertTrue(all(j['state']=='awaiting_review' for j in result['jobs']))

    def test_cancel_prevents_dispatch(self):
        runner = Runner(self.library, DemoProvider())
        runner.cancel()
        result = runner.run(["Reading place"])
        self.assertEqual(result["calls"], 0)
        self.assertEqual(result["jobs"][0]["state"], "cancelled")

    def test_job_history_is_bounded_without_deleting_previous_jobs(self):
        with patch('living_world.workshop.library.MAX_STORED_JOBS', 2):
            ids = [self.library.create_job('Reading place', 'fixture', 'offline') for _ in range(2)]
            with self.assertRaisesRegex(ValueError, 'history limit'):
                self.library.create_job('Another place', 'fixture', 'offline')
        self.assertEqual({j['id'] for j in self.library.jobs()}, set(ids))

    def test_building_profile_changes_invalidate_library_revision(self):
        from living_world.generation.civic_catalog import BUILDING_TEMPLATES
        before = self.library.snapshot()['revision']
        with patch.dict(BUILDING_TEMPLATES['school'], {'name': 'Changed school profile'}):
            self.assertNotEqual(self.library.snapshot()['revision'], before)
        self.assertEqual(self.library.snapshot()['revision'], before)

    def test_authoring_rejects_rebinding_hosts_and_full_history(self):
        with TestClient(create_app(':memory:')) as client:
            url = '/api/workshop/requests'
            self.assertEqual(client.post(url, json={}, headers={'Host':'evil.invalid','Origin':'http://evil.invalid'}).status_code, 403)
            self.assertEqual(client.post(url, json={}, headers={'Host':'evil.invalid'}).status_code, 403)
            self.assertEqual(client.post(url, json={}).status_code, 200)
            self.assertEqual(client.get('/agent_workshop.html').status_code, 200)
            with patch('living_world.workshop.library.MAX_STORED_JOBS', 1):
                self.assertEqual(client.post(url, json={}).status_code, 409)
                self.assertEqual(client.post('/api/workshop/demo', json={}).status_code, 409)

    def test_preview_hash_must_match_the_reviewed_draft(self):
        job = Runner(self.library, DemoProvider()).run(["Leseplätze prüfen"])["jobs"][0]
        with self.assertRaisesRegex(ValueError, "viewed draft changed"):
            self.library.publish(job["id"], "Tester", visual_reviewed=True, expected_pack_hash="0"*64)
        self.assertEqual(self.library.job(job["id"])["state"], "awaiting_review")

    def test_parallel_name_collisions_are_rechecked_at_publication(self):
        result = Runner(self.library, DemoProvider()).run(["Leseplätze links", "Leseplätze rechts"])
        first, second = result["jobs"]
        self.library.publish(first["id"], "Prüfer", visual_reviewed=True)
        with self.assertRaisesRegex(ValueError, "Current library rejects"):
            self.library.publish(second["id"], "Prüfer", visual_reviewed=True)
        self.assertEqual(self.library.job(second["id"])["state"], "rejected")
        self.assertEqual(len(self.library.inventory()["publications"]), 1)

    def test_reject_unknown_references_actions_code_and_sprite_overflow(self):
        original = self.draft()
        changes = [lambda p: p["rooms"][0]["required"].append("missing_object"),
                   lambda p: p["objects"][0]["actions"].append("execute_shell"),
                   lambda p: p["objects"][0].update(code="delete files"),
                   lambda p: p["objects"][0]["pixels"][0].update(w=144),
                   lambda p: p["objects"][0]["actions"].append("sleep"),
                   lambda p: p["rooms"][0].update(width=5, min_width=6)]
        for change in changes:
            pack = deepcopy(original); change(pack)
            with self.subTest(pack=pack["id"]):
                report = self.library.validate(pack)
                self.assertFalse(report["valid"])
                self.assertTrue(report["errors"])
        self.assertEqual(self.library.inventory()["publications"], [])

    def test_unplaceable_required_program_does_not_publish(self):
        pack = self.draft()
        pack["rooms"][0]["width"] = pack["rooms"][0]["min_width"] = 5
        pack["rooms"][0]["height"] = pack["rooms"][0]["min_height"] = 5
        # Impossible by area alone; bounded search must reject, never omit.
        pack["rooms"][0]["required"] = ["bed_king"] * 4 + [pack["objects"][0]["id"]]
        report = self.library.validate(pack)
        self.assertFalse(report["valid"])
        self.assertEqual(report["room_checks"], 8)

    def test_library_persists_and_reloads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"workshop.sqlite3"
            lib = Library(path)
            job = Runner(lib, DemoProvider()).run(["Persistenter Leseplatz"])["jobs"][0]
            lib.publish(job["id"], "Tester", visual_reviewed=True)
            revision = lib.inventory()["revision"]
            lib.close()
            reloaded = Library(path)
            self.assertEqual(reloaded.inventory()["revision"], revision)
            self.assertEqual(reloaded.job(job["id"])["state"], "published")
            reloaded.close()

    def test_publication_is_serialized_across_database_connections(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'workshop.sqlite3'
            a, b = Library(path), Library(path)
            try:
                jobs = Runner(a,DemoProvider()).run(['Leseplatz A','Leseplatz B'])['jobs']
                def publish(pair):
                    lib, job = pair
                    try:
                        return lib.publish(job['id'],'Tester',visual_reviewed=True)['state']
                    except ValueError:
                        return 'rejected'
                with ThreadPoolExecutor(max_workers=2) as pool:
                    states = list(pool.map(publish, [(a,jobs[0]),(b,jobs[1])]))
                self.assertCountEqual(states,['published','rejected'])
                self.assertEqual(len(a.inventory()['publications']),1)
            finally:
                a.close(); b.close()

    def test_api_isolation_preview_publication_and_reuse(self):
        with TestClient(create_app(":memory:")) as client:
            client.post('/api/control', json={'paused': True})
            before = client.get('/api/export').json()
            self.assertEqual(client.get('/workshop').status_code, 200)
            self.assertFalse(client.get('/api/workshop/jobs').json()['external_enabled_in_web'])
            self.assertEqual(client.post('/api/workshop/demo', json={}, headers={'Origin':'https://untrusted.invalid'}).status_code, 403)
            result = client.post('/api/workshop/demo', json={}).json()
            job = result['jobs'][0]
            self.assertEqual(job['state'], 'awaiting_review')
            self.assertEqual(client.post(f"/api/workshop/jobs/{job['id']}/publish", json={'reviewer':'Tester'}).status_code, 409)
            self.assertEqual(client.post(f"/api/workshop/jobs/{job['id']}/publish", json={'reviewer':'Tester','visual_reviewed':True,'expected_pack_hash':job['report']['pack_hash']}).status_code, 200)
            room = client.post('/api/workshop/room', json={'kind': job['pack']['rooms'][0]['id']}).json()
            self.assertTrue(room['validation']['valid'])
            self.assertTrue(any('procedural_sprite' in o for o in room['objects']))
            self.assertEqual(client.get('/api/export').json(), before)


class ProviderTests(unittest.TestCase):
    def test_explicit_external_optin_and_exact_model_are_required(self):
        with self.assertRaises(ProviderError):
            ApiProvider(ProviderConfig('openrouter','vendor/model'))
        with self.assertRaises(ValueError):
            ProviderConfig('openrouter','bad model;command')

    def test_provider_requests_and_parsers_without_network_or_real_keys(self):
        for provider, response in (
            ('openai', {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"answer":1}'}]}],'usage':{'input_tokens':5}}),
            ('gemini', {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"answer":1}'}]}}],'usageMetadata':{'promptTokenCount':5}}),
            ('openrouter', {'choices':[{'finish_reason':'stop','message':{'content':'{"answer":1}'}}],'usage':{'prompt_tokens':5}}),
        ):
            calls = []
            def transport(*args):
                calls.append(args)
                return response
            with self.subTest(provider=provider), patch.dict('os.environ', {'OPENAI_API_KEY':'test-placeholder','GEMINI_API_KEY':'test-placeholder','OPENROUTER_API_KEY':'test-placeholder'}):
                p = ApiProvider(ProviderConfig(provider,'vendor-model'), allow_external=True, transport=transport)
                data, usage = p.complete('author JSON', {'type':'object'})
                self.assertEqual(data, {'answer':1})
                self.assertTrue(usage)
                self.assertNotIn('test-placeholder', json.dumps(calls[0][2]))
                self.assertTrue(calls[0][0].startswith('https://'))
                self.assertNotIn('test-placeholder', calls[0][0])

    def test_model_listing_does_not_silently_substitute_models(self):
        with patch.dict('os.environ', {'OPENROUTER_API_KEY':'test-placeholder'}):
            p = ApiProvider(ProviderConfig('openrouter','unknown/model'), allow_external=True,
                            transport=lambda *a: {'data':[{'id':'known/model'}]})
            with self.assertRaisesRegex(ProviderError,'no substitution'):
                p.verify_model()

    def test_truncated_output_is_not_accepted_as_implementation(self):
        with patch.dict('os.environ', {'OPENROUTER_API_KEY':'test-placeholder'}):
            p = ApiProvider(ProviderConfig('openrouter','vendor/model'), allow_external=True,
                            transport=lambda *a: {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]})
            with self.assertRaisesRegex(ProviderError,'incomplete'):
                p.complete('JSON',{})


if __name__ == '__main__':
    unittest.main()
