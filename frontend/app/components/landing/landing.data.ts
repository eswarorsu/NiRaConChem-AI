import { CATALOG_COUNTS, CATALOG_PRODUCTS, type CatalogProduct } from "./catalog.data";

/**
 * Everything the landing page shows that is not layout.
 *
 * Product facts are looked up from catalog.data.ts (generated from the
 * application's own catalog) — the page never restates a manufacturer claim by
 * hand. Scene coordinates come from the Blender renders in public/landing/ and
 * are fractions of the 16:9 hero frame, measured from the top-left corner.
 */

function product(name: string): CatalogProduct {
  const found = CATALOG_PRODUCTS.find((item) => item.name === name);
  if (!found) throw new Error(`landing.data: "${name}" is not in catalog.data.ts`);
  return found;
}

export type SpotKey = "roof" | "facade" | "joints" | "repair";

export type Spot = {
  key: SpotKey;
  /** Tab label — the part of the building. */
  label: string;
  product: CatalogProduct;
  /** One sentence, paraphrasing the datasheet's own description. */
  summary: string;
  /** A single figure quoted from the datasheet. */
  fact: { term: string; value: string };
};

const roof = product("Sikalastic®-841 ST");
const facade = product("Sikagard®-550 W Elastic (G)");
const joints = product("Sikaflex®-11 FC+");
const repair = product("Sika MonoTop®-620 AE");

export const SPOTS: Spot[] = [
  {
    key: "roof",
    label: "Roof",
    product: roof,
    summary: "Liquid-applied pure polyurea membrane, fast curing and suited to hot, tropical climates.",
    fact: { term: "Crack bridging", value: "Class A5 static, B4.2 dynamic" },
  },
  {
    key: "facade",
    label: "Facade",
    product: facade,
    summary: "Plasto-elastic coating that bridges cracks and holds back carbonation and chlorides.",
    fact: { term: "Crack bridging", value: "Class A4, over 1.25 mm" },
  },
  {
    key: "joints",
    label: "Joints",
    product: joints,
    summary: "One-part elastic sealant and adhesive that bonds most construction substrates.",
    fact: { term: "Service temperature", value: "−40 °C to +80 °C" },
  },
  {
    key: "repair",
    label: "Repair",
    product: repair,
    summary: "Polymer-modified finishing mortar with silica fume, for sealing concrete repair patches.",
    fact: { term: "Bond strength", value: "about 1.0 N/mm² (EN 1542)" },
  },
];

/** Placement of the cut-out villa render inside the hero frame. */
export const VILLA_BOX = { left: 0.3691, top: 0.4264, width: 0.6309, height: 0.3889 };

/** A Gulf roof, bottom to top — the order it is built in. */
export type Layer = { key: string; name: string; note: string };

export const LAYERS: Layer[] = [
  { key: "slab", name: "Concrete slab", note: "Its age, moisture and falls decide what can go on top." },
  { key: "primer", name: "Primer", note: "Seals the pores and gives the membrane something to grip." },
  { key: "membrane", name: "Waterproofing membrane", note: "The layer that actually keeps water out, summer after Gulf summer." },
  { key: "insulation", name: "Insulation board", note: "Holds the heat off the slab and the rooms below it." },
  { key: "screed", name: "Screed", note: "Builds the falls that walk water to the drains." },
  { key: "tiles", name: "Tile finish", note: "Its adhesive and joints take the same heat as everything under it." },
];

export const COUNTS = {
  profiles: CATALOG_COUNTS.profiles,
  manufacturers: CATALOG_COUNTS.brandLogos,
};

/** Wordmarks shown in the sources strip, in the order they read best. */
export const MAKERS: { src: string; name: string; width: number; height: number }[] = [
  { src: "/landing/maker-sika.webp", name: "Sika", width: 209, height: 240 },
  { src: "/brands/mapei.png", name: "Mapei", width: 330, height: 77 },
  { src: "/brands/fosroc.jpg", name: "Fosroc", width: 709, height: 768 },
  { src: "/brands/kerakoll.svg", name: "Kerakoll", width: 570, height: 125 },
  { src: "/brands/laticrete.svg", name: "Laticrete", width: 231, height: 164 },
  { src: "/brands/tremco.svg", name: "Tremco", width: 185, height: 61 },
  { src: "/brands/fischer.png", name: "fischer", width: 3088, height: 488 },
  { src: "/brands/conmix.png", name: "Conmix", width: 280, height: 130 },
];

/** Where each layer's number sits on its render: the left end of its top face. */
export const LAYER_TAGS: { x: number; y: number }[] = [
  { x: 0.1352, y: 0.524 },
  { x: 0.2072, y: 0.4897 },
  { x: 0.2768, y: 0.4441 },
  { x: 0.3441, y: 0.3539 },
  { x: 0.41, y: 0.2811 },
  { x: 0.4746, y: 0.2285 },
];
