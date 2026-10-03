"""Executable neighborhood services, separate from future occupation simulators."""

def service(label,kinds,duration,relief,cost=0,preference='socializing'):
    return {'label':label,'object_kinds':kinds,'duration':duration,'relief':relief,
            'cost':cost,'preference':preference,'thought':f'I would like to: {label.lower()}.','income':0}

SERVICE_ACTIONS={
    'exercise_gym':service('Training at the gym',['gym_station'],1200,{'fun':.62,'comfort':.15},6,'walking'),
    'dance_club':service('Dancing at the nightclub',['nightclub_floor'],900,{'fun':.68,'social':.15},8),
    'visit_townhall':service('Taking care of paperwork',['townhall_desk'],600,{'comfort':.12},0,'reading'),
    'visit_clinic':service('Attending a clinic appointment',['hospital_desk'],900,{'comfort':.18},5),
    'visit_fire_station':service('Visiting the fire station open desk',['fire_stationdesk'],600,{'fun':.22},0,'reading'),
    'browse_mall':service('Browsing the shopping center',['mall_counter'],900,{'fun':.42},0,'walking'),
    'school_day':service('Attending class',['school_student_chair'],3600,{'fun':.08,'social':.08},0,'reading'),
    'kindergarten_day':service('Playing and learning at kindergarten',['kindergarten_mat'],3600,{'fun':.22,'social':.12},0,'socializing'),
    'visit_pool':service('Swimming at the pool',['pool_water'],1500,{'fun':.58,'comfort':.12},4,'walking'),
    'visit_bar':service('Meeting friends at the bar',['bar_counter'],900,{'fun':.38,'social':.25},7,'socializing'),
    'community_meet':service('Joining a neighborhood gathering',['community_table'],1200,{'fun':.35,'social':.32},0,'socializing'),
    'visit_patient':service('Visiting someone at hospital',['hospital_bed'],600,{'social':.24,'comfort':.06},0,'socializing'),
}
SERVICE_JOBS={
    'Nurse':('hospital_desk','hospital'),'Firefighter':('fire_stationdesk','fire_station'),
    'Civic clerk':('townhall_desk','townhall'),'Office analyst':('office_station','office'),
    'Fitness coach':('gym_station','gym'),'Retail assistant':('supermarket_checkout','supermarket'),
}

def service_available(actor,kind,now):
    age=actor.get('age',30)
    if kind=='kindergarten_day':return 4<=age<7 and 8*3600<=now%86400<15*3600
    if kind=='school_day':return 7<=age<18 and 8*3600<=now%86400<15*3600
    if kind=='visit_bar':return age>=18 and (now%86400>=16*3600 or now%86400<1*3600)
    if kind=='visit_pool':return age>=7 and 8*3600<=now%86400<21*3600
    if kind=='community_meet':return 9*3600<=now%86400<21*3600
    if kind=='visit_patient':return 10*3600<=now%86400<19*3600
    if kind=='dance_club':return now%86400>=18*3600 or now%86400<2*3600
    if kind in {'visit_townhall','visit_clinic','visit_fire_station'}:
        return 9*3600<=now%86400<17*3600 and actor.get('cooldowns',{}).get(kind,0)<=now
    if kind=='exercise_gym':return actor['needs'].get('fatigue',0)<.75
    return True

def assigned_service_job(actor,objects):
    job=SERVICE_JOBS.get(actor['profile']['job'])
    if not job:return actor.get('workplace')
    found=next((o for o in objects.values() if o['kind']==job[0]),None)
    return {'target_id':found['id'],'building_id':found['building_id'],'workplace_id':found['building_id'],
            'station_kind':found['kind'],'work_from_home':False} if found else actor.get('workplace')
