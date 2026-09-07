/**
 * catalog.data.ts — GENERATED, do not hand-edit.
 *
 * Every value below is copied verbatim out of the application's own catalog:
 *   - product records  ->  data/vector_store/product_profiles.json
 *   - market counts    ->  app/data/qcon-market-products.json
 *   - brand logo count ->  public/brands/manifest.json
 *
 * Nothing here is written by hand, so the landing page cannot state a
 * manufacturer claim, certification or performance figure that the platform
 * does not actually hold. Regenerate with scripts/generate-landing-catalog.py.
 */

export type CatalogPerformance = Record<string, string>;

export type CatalogProduct = {
  name: string;
  manufacturer: string;
  tagline: string;
  description: string;
  usage: string;
  systemType: string;
  category: string;
  applicationAreas: string[];
  climateStrengths: string[];
  performance: CatalogPerformance;
  documents: string[];
  productUrl: string;
  datasheetUrl: string;
  country: string;
};

export const CATALOG_COUNTS = {
  "profiles": 1540,
  "marketProducts": 423,
  "marketCategories": 32,
  "brandLogos": 23
} as const;

export const CATALOG_PRODUCTS: CatalogProduct[] = [
  {
    "name": "Sikalastic®-841 ST",
    "manufacturer": "Sika",
    "tagline": "Liquid applied pure polyurea membrane",
    "description": "Sikalastic®-841 ST is a two part, elastic, 100 % solids, very fast curing and coloured pure polyurea liquid applied membrane with good chemical resistance. Suitable for use in hot and tropical climatic conditions.",
    "usage": "Bridge deck waterproofing membrane; Abrasion resistant protective coating in industrial and manufacturing facilities; Waterproofing for cut and cover structures; Waterproofing for submersed structures; Waterproofing on walkways and balconies; Waterproofing on floors and car park decks; Water retaining structures in power plants; Secondary containment structures; Tank, bund and pit lining in sewage and waste water treatment plants",
    "systemType": "Liquid-applied waterproofing membrane system",
    "category": "waterproofing",
    "applicationAreas": [
      "roof",
      "balcony",
      "parking"
    ],
    "climateStrengths": [
      "UAE/GCC climate",
      "roof waterproofing",
      "local availability"
    ],
    "performance": {
      "shore_d_hardness": "~45 - 50: (DIN 53505)",
      "tensile_strength": "> 15 N/mm²: (DIN 53504)",
      "crack_bridging": "Class A5: Static; Class B4.2: Dynamic"
    },
    "documents": [
      "PDS"
    ],
    "productUrl": "https://gcc.sika.com/en/construction/waterproofing/liquid-applied-membrane/sikalastic-841-st.html",
    "datasheetUrl": "https://gcc.sika.com/dms/getdocument.get/b5ebe5d1-b676-4215-8aa2-7efb49d24156/sikalastic_-841_st.pdf",
    "country": "UAE"
  },
  {
    "name": "Sikafloor®-2200",
    "manufacturer": "Sika",
    "tagline": "High strength epoxy repair filler for horizontal cracks and minor repairs in concrete substrates",
    "description": "Sikafloor®-2200 is an epoxy filler compound. It is a two component, fine aggregate filled, fast curing material, ideal for minor horizontal concrete repair applications. Sikafloor®-2200 is an easily workable filler compound that can be applied by either trowel, spatula or knife. It cures to give high mechanical properties typical of epoxy compounds. It is resistant to oils, greases, petroleum, salts, many acids and alkalis and most commonly met corrosive media. It does not shrink on curing, its impact resistance and mechanical strength is greater than that of concrete.",
    "usage": "Repairing surface defects such as blowholes and pin holes in concrete floors; Dowel bars anchoring",
    "systemType": "Industrial resin flooring system",
    "category": "flooring",
    "applicationAreas": [
      "industrial floor"
    ],
    "climateStrengths": [
      "concrete repair",
      "flooring",
      "UAE/GCC climate",
      "local availability"
    ],
    "performance": {
      "compressive_strength": "≥ 80 MPa (Cured 7 days at 40°C): (ASTM C579)",
      "bond_strength": "≥ 2.5 N/mm2(or concrete failure): (ASTM D4541 / BS 1881, Part 207)",
      "service_temperature": "Sikafloor®-2200 is designed to be used when cured from below freezing point to 60°C.; Note: Sikafloor®-2200 will cure at temperatures as low as 0°C, although at low temperatures cure is retarded.",
      "chemical_resistance": "Sikafloor®-2200 has excellent resistance to the following: Most aqueous solutions, sewage, urine, fresh water, sea water, diluted and concentrated alkalis, diluted acids, sulphur gases, mineral, vegetable and animal oils"
    },
    "documents": [
      "Product Data Sheet (PDS)"
    ],
    "productUrl": "https://gcc.sika.com/en/construction/flooring-and-coating/industrial-flooring/accessories/sikafloor-2200.html",
    "datasheetUrl": "https://gcc.sika.com/dam/dms/gcc/c/pds-sikafloor-2200.pdf",
    "country": "UAE"
  },
  {
    "name": "Sika MonoTop®-620 AE",
    "manufacturer": "Sika",
    "tagline": "one component, polymer modified, finishing mortar and Fairing Coat",
    "description": "Sika MonoTop®-620 AE is a polymer modified cementitious mortar containing silica fume for use as a finishing and protective top coat for concrete repair patches. Suitable for use in hot and tropical climatic conditions.",
    "usage": "Pore sealer / finishing coat on cementitious substrates; Thin layer render coat on horizontal and vertical areas in building and civil engineering construction, for external and internal finishing etc.; Levelling mortar on uneven substrates, and profiled concrete surfaces.; Fine repair mortar to fill honeycombs, pores etc.; Repair mortar for repair of small defects on edges and joint sides; to form and finish joints and covings.",
    "systemType": "Concrete repair mortar system",
    "category": "repair",
    "applicationAreas": [
      "concrete repair",
      "facade"
    ],
    "climateStrengths": [
      "UAE/GCC climate",
      "concrete repair",
      "local availability"
    ],
    "performance": {
      "compressive_strength": "W/P ratio: 28 days; 0.20: ~25 N/mm2",
      "bond_strength": "~1.0 N/mm2: (EN 1542)"
    },
    "documents": [
      "Product Data Sheet (PDS)"
    ],
    "productUrl": "https://gcc.sika.com/en/construction/refurbishment/concrete-repair/sika-monotop-620ae.html",
    "datasheetUrl": "https://gcc.sika.com/dam/dms/gcc/k/sika_monotop_-620ae.pdf",
    "country": "UAE"
  },
  {
    "name": "Sikagard®-550 W Elastic (G)",
    "manufacturer": "Sika",
    "tagline": "CRACK BRIDGING AND ANTI-CARBONATION PROTECTIVE COATING FOR CONCRETE",
    "description": "Sikagard®-550 W Elastic (G) is a one component, plasto-elastic coating based on acrylic dispersion with excellent crack-bridging properties. It has excellent resistance against carbonation and ingress of chloride ions, sulphates and oxygen. Suitable for use in hot and tropical climatic conditions.",
    "usage": "Sikagard®-550 W Elastic (G) is used for protection and enhancement of concrete structures (normal and lightweight concrete), especially exposed outdoor concrete surfaces with a risk of cracking.; Sikagard®-550 W Elastic (G) is used with concrete repair works as an elastic protective coating on Sika® smoothing mortars (SikaRep®, Sika Monotop® range), fibre cement and overcoating of existing soundly adhering coatings.; Can be applied on various substrates such as bricks, masonry, concrete blocks, and metal elements such as aluminum sections.; Damp proof coating on facades for high rise and low rise residential, commercial, institutional buildings, etc.; Vapor control layer for facade application.; Comprehensive barrier against carbon dioxide, water, sulphates and chloride ions.; Bridge, highway structures and underpasses.; Multi storey car parks and underground garages.",
    "systemType": "Concrete protective coating system",
    "category": "coating",
    "applicationAreas": [
      "roof",
      "parking",
      "concrete repair",
      "facade"
    ],
    "climateStrengths": [
      "UAE/GCC climate",
      "concrete repair",
      "local availability"
    ],
    "performance": {
      "crack_bridging": "Class A 4 (> 1.25 mm): (UNE-EN 1062-7:2004 Method A - C.2); Class B.3.1: (UNE-EN 1062-7:2004 Method B - B.3.1)",
      "bond_strength": "≥ 1,5 N/mm2(or concrete failure): (ASTM D4541)",
      "reaction_to_fire": "lab result: Class A - requirements; Flame Spread Index (FSI): 15: 0 - 25; Smoke Development Index (SDI): 0: 0 - 450"
    },
    "documents": [
      "Product Data Sheet (PDS)"
    ],
    "productUrl": "https://gcc.sika.com/en/construction/refurbishment/concrete-protection/sikagard-550-w-elasticg.html",
    "datasheetUrl": "https://gcc.sika.com/dam/dms/gcc/b/sikagard_-550_w_elasticg.pdf",
    "country": "UAE"
  },
  {
    "name": "Sikaflex®-11 FC+",
    "manufacturer": "Sika",
    "tagline": "Multipurpose elastic adhesive and joint sealant",
    "description": "Sikaflex®-11 FC+ is a 1-part, multipurpose elastic adhesive and joint sealant with very good application properties which bonds and seals most construction material substrates. Internal and external use.",
    "usage": "Concrete; Masonry; Reconstituted or cast stone; Ceramic; Wood; Metal; Glass",
    "systemType": "Sealant system",
    "category": "sealant",
    "applicationAreas": [
      "joint"
    ],
    "climateStrengths": [
      "joint sealing",
      "UAE/GCC climate",
      "local availability"
    ],
    "performance": {
      "shore_a_hardness": "~37 (after 28 days): (ISO 868)",
      "tensile_strength": "~1,5 N/mm2: (ISO 37)",
      "chemical_resistance": "Resistant to many chemicals. Contact Sika® Technical Services for additional information.",
      "service_temperature": "−40 °C min. / +80 °C max."
    },
    "documents": [
      "Product Data Sheet (PDS)"
    ],
    "productUrl": "https://gcc.sika.com/en/construction/sealing-bonding/sealing-bonding-solutions/sikaflex-11-fc.html",
    "datasheetUrl": "https://gcc.sika.com/dam/dms/gcc/o/sikaflex_-11_fc_.pdf",
    "country": "UAE"
  }
];
