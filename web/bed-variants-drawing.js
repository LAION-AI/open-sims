/* Embeddable, code-drawn pixel beds for the additive bed variant catalog. */
const bedFill = (c, x, y, w, h, color) => {
  c.fillStyle = color;
  c.fillRect(x, y, w, h);
};

/** Draw a bed variant at the current 24-pixels-per-meter object origin.
 * Returns true when the kind is one of this module's variants, false otherwise.
 */
export function drawBedVariant(c, o, palette) {
  const known = new Set([
    'bed_storage_single', 'bed_loft', 'bed_bunk', 'bed_queen', 'bed_king',
    'bed_platform_double', 'bed_foldaway_guest', 'bed_hospital',
  ]);
  if (!known.has(o.kind)) return false;

  const s = 24, w = o.base_w * s, h = o.base_h * s;
  const fabric = palette.fabric || '#8aa486';
  const wood = '#a98762', paleWood = '#d3b38a', linen = '#f1e7cf';
  const shade = '#596858';
  const mattress = (top = 4, bottom = h - 3, inset = 3) => {
    bedFill(c, 1, top, w - 2, bottom - top, wood);
    bedFill(c, 3, top + 2, w - 6, bottom - top - 5, linen);
    bedFill(c, 4, top + Math.max(8, (bottom - top) * .42), w - 8,
      Math.max(4, bottom - top - Math.max(8, (bottom - top) * .42) - 5), fabric);
    bedFill(c, 4, top + Math.max(8, (bottom - top) * .42), w - 8, 2, '#ffffff38');
    for (let xx = 6; xx < w - 8; xx += 24) {
      bedFill(c, xx, top + 4, 14, 9, '#faf2dc');
      bedFill(c, xx, top + 13, 14, 2, '#d7cdb5');
    }
  };

  switch (o.kind) {
    case 'bed_storage_single':
      bedFill(c, 2, 2, w - 4, h - 3, wood);
      bedFill(c, 4, 4, w - 8, h - 9, '#876e50');
      bedFill(c, 7, 8, w - 14, h - 17, paleWood);
      bedFill(c, 9, 10, w - 18, h - 21, '#b8956c');
      bedFill(c, w / 2 - 3, h - 11, 6, 2, '#ead6ad');
      mattress(3, h - 8, 3);
      break;
    case 'bed_loft':
      bedFill(c, 2, 2, w - 4, h - 3, '#78866d');
      bedFill(c, 4, 4, w - 8, h - 9, wood);
      mattress(3, h - 10);
      bedFill(c, 1, 3, 3, h - 6, paleWood);
      bedFill(c, w - 4, 3, 3, h - 6, paleWood);
      bedFill(c, 3, h - 7, w - 6, 3, '#74866e');
      for (let yy = 5; yy < h - 5; yy += 6) bedFill(c, 2, yy, w - 4, 1, '#e1d0aa');
      bedFill(c, 4, h - 4, 2, 4, shade);
      bedFill(c, w - 6, h - 4, 2, 4, shade);
      break;
    case 'bed_bunk':
      bedFill(c, 2, 1, w - 4, h - 2, wood);
      bedFill(c, 4, 4, w - 8, 5, linen);
      bedFill(c, 4, 6, w - 8, 3, fabric);
      bedFill(c, 4, h - 10, w - 8, 5, linen);
      bedFill(c, 4, h - 8, w - 8, 3, fabric);
      bedFill(c, 1, 2, 3, h - 4, paleWood);
      bedFill(c, w - 4, 2, 3, h - 4, paleWood);
      for (let yy = 3; yy < h - 3; yy += 5) bedFill(c, 1, yy, w - 2, 1, '#f3dfb8');
      bedFill(c, 1, h - 5, w - 2, 2, '#71806b');
      break;
    case 'bed_queen':
    case 'bed_king':
      bedFill(c, 1, 1, w - 2, h - 1, '#8b7155');
      bedFill(c, 2, 1, w - 4, 5, paleWood);
      mattress(4, h - 3);
      bedFill(c, 2, h - 5, w - 4, 3, wood);
      if (o.kind === 'bed_king') {
        bedFill(c, 3, 3, w - 6, 2, '#e8cf9e');
        bedFill(c, w / 2 - 1, 8, 2, h - 16, '#ffffff27');
      }
      break;
    case 'bed_platform_double':
      bedFill(c, 0, 3, w, h - 2, '#8b7155');
      bedFill(c, 2, 2, w - 4, h - 6, paleWood);
      bedFill(c, 3, 4, w - 6, h - 10, '#b99a70');
      mattress(4, h - 5);
      bedFill(c, 2, h - 5, w - 4, 3, '#80664d');
      for (let xx = 5; xx < w - 3; xx += 8) bedFill(c, xx, h - 2, 2, 2, '#685945');
      break;
    case 'bed_foldaway_guest':
      bedFill(c, 1, 1, w - 2, h - 2, '#748276');
      bedFill(c, 3, 3, w - 6, h - 6, linen);
      bedFill(c, 5, 7, w - 10, h - 12, fabric);
      bedFill(c, 5, 5, w - 10, 3, '#faf2dc');
      bedFill(c, 1, h - 5, w - 2, 3, wood);
      bedFill(c, 3, h - 2, 3, 2, shade);
      bedFill(c, w - 6, h - 2, 3, 2, shade);
      bedFill(c, w - 5, 3, 2, h - 8, '#dce2d2');
      break;
    case 'bed_hospital':
      bedFill(c, 1, 2, w - 2, h - 4, '#87978d');
      bedFill(c, 4, 5, w - 8, h - 12, '#dce3d6');
      bedFill(c, 6, 8, w - 12, h - 18, '#a9c5bb');
      bedFill(c, 7, 9, w - 14, 2, '#f5edda');
      bedFill(c, 2, 4, 2, h - 8, '#e4e5d6');
      bedFill(c, w - 4, 4, 2, h - 8, '#e4e5d6');
      bedFill(c, 1, 3, w - 2, 2, '#e5e4d4');
      bedFill(c, 1, h - 5, w - 2, 2, '#e5e4d4');
      bedFill(c, 4, h - 3, 3, 3, shade);
      bedFill(c, w - 7, h - 3, 3, 3, shade);
      bedFill(c, w - 10, 3, 3, 3, '#647f75');
      bedFill(c, w - 8, 4, 1, 1, '#d9c78e');
      break;
  }
  return true;
}
