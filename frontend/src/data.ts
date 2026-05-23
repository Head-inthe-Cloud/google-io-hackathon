import { StylePreference, ClosetItem } from "./types";

export const STYLE_PREF_CHOICES: StylePreference[] = [
  {
    id: "minimalist",
    name: "Minimalist Casual",
    chineseName: "Minimal Casual",
    description: "Neutral tones, clean cuts, versatile basics, and soft textures emphasizing understated luxury.",
    vibeText: "Relaxed daily confidence",
    imageUrl: "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&q=80&w=600"
  },
  {
    id: "streetwear",
    name: "Streetwear & Grunge",
    chineseName: "Streetwear",
    description: "Relaxed oversized silhouettes, bold coordinates, utility details, and contrasting layers.",
    vibeText: "Bold, modern self-expression",
    imageUrl: "https://images.unsplash.com/photo-1509281373149-e957c6296406?auto=format&fit=crop&q=80&w=600"
  },
  {
    id: "business",
    name: "Smart Commuter & Corporate",
    chineseName: "Smart Commute",
    description: "Tailored blazers, structural trousers, clean collars, and sophisticated office-to-dinner fits.",
    vibeText: "Sharp, elegant posture",
    imageUrl: "https://images.unsplash.com/photo-1485968579580-b6d095142e6e?auto=format&fit=crop&q=80&w=600"
  },
  {
    id: "vintage",
    name: "Vintage & Retro Romantic",
    chineseName: "Retro Romantic",
    description: "Warm earth tones, corduroy, tweed, nostalgic knit patterns, and classic heritage leather pieces.",
    vibeText: "Timeless nostalgic grace",
    imageUrl: "https://images.unsplash.com/photo-1537989370856-8f3b61f77459?auto=format&fit=crop&q=80&w=600"
  },
  {
    id: "preppy",
    name: "Classic Prep / Academic",
    chineseName: "Classic Prep",
    description: "Cable-knit v-necks, pleated bottoms, collared oxfords, and structured smart loafers.",
    vibeText: "Polished, literary spirit",
    imageUrl: "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&q=80&w=600"
  },
  {
    id: "gorpcore",
    name: "Sporty & Gorpcore",
    chineseName: "Sporty Gorpcore",
    description: "Technical weatherproof shell jackets, utility cargo shapes, clean hiking boots, and high performance.",
    vibeText: "Active adventure aesthetic",
    imageUrl: "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?auto=format&fit=crop&q=80&w=600"
  }
];

export interface QuizOutfit {
  id: string;
  aesthetic: string;
  description: string;
  imageUrl: string;
  tags: string[];
  gender: "male" | "female" | "unisex";
}

export const STYLE_QUIZ_OUTFITS: QuizOutfit[] = [
  // --- FEMALE SELECTIONS ---
  {
    id: "q-f1",
    aesthetic: "Minimalist Casual",
    description: "Tailored beige lightweight blazer, loose linen cream trousers, ribbed vest",
    imageUrl: "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=600",
    tags: ["minimal", "clean", "neutral"],
    gender: "female"
  },
  {
    id: "q-f2",
    aesthetic: "Streetwear Grunge",
    description: "Wash-black oversized graphic jacket, chunky distressed combat boots, tiered combat skirt",
    imageUrl: "https://images.unsplash.com/photo-1509281373149-e957c6296406?auto=format&fit=crop&q=80&w=600",
    tags: ["oversized", "street", "grunge"],
    gender: "female"
  },
  {
    id: "q-f3",
    aesthetic: "Classic Prep",
    description: "V-neck collegiate knit pullover, crisp accordion pleated skirt, patent-leather penny loafers",
    imageUrl: "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&q=80&w=600",
    tags: ["classic", "collegiate", "preppy"],
    gender: "female"
  },
  {
    id: "q-f4",
    aesthetic: "Cottagecore Romantic",
    description: "Sage linen milkmaid midi dress with puff-sleeves, straw tote bags, floral hair ribbon",
    imageUrl: "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&q=80&w=600",
    tags: ["organic", "vintage", "soft"],
    gender: "female"
  },
  {
    id: "q-f5",
    aesthetic: "Athleisure Active",
    description: "Woven high-contrast running vest, spandex biker shorts, chunky lightweight sneakers",
    imageUrl: "https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?auto=format&fit=crop&q=80&w=600",
    tags: ["sporty", "sleek", "functional"],
    gender: "female"
  },
  {
    id: "q-f6",
    aesthetic: "Smart Executive",
    description: "Double-breasted cocoa blazer, pleated terracotta high-waisted trousers, elegant sandals",
    imageUrl: "https://images.unsplash.com/photo-1485968579580-b6d095142e6e?auto=format&fit=crop&q=80&w=600",
    tags: ["tailored", "office", "sharp"],
    gender: "female"
  },
  {
    id: "q-f7",
    aesthetic: "Bohemian Artisanal",
    description: "Tassel crochet wrap crop-top, earthy wrap-around tier maxi skirt, silver-threaded rings",
    imageUrl: "https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&q=80&w=600",
    tags: ["breezy", "expressive", "artisanal"],
    gender: "female"
  },
  {
    id: "q-f8",
    aesthetic: "Quiet Luxury",
    description: "Draped camel cashmere belted trench, silk tie neck accent, structured small leather clutch",
    imageUrl: "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&q=80&w=600",
    tags: ["timeless", "sophisticated", "clean"],
    gender: "female"
  },

  // --- MALE SELECTIONS ---
  {
    id: "q-m1",
    aesthetic: "Minimalist Casual",
    description: "Tailored oatmeal crewneck sweater, relaxed-fit beige trousers, clean white leather trainers",
    imageUrl: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&q=80&w=600",
    tags: ["minimal", "clean", "neutral"],
    gender: "male"
  },
  {
    id: "q-m2",
    aesthetic: "Streetwear Grunge",
    description: "Relaxed drop-shoulder graphite hoodie, utilitarian cargo pants, high-top skate sneakers",
    imageUrl: "https://images.unsplash.com/photo-1516257984-b1b4d707412e?auto=format&fit=crop&q=80&w=600",
    tags: ["oversized", "street", "grunge"],
    gender: "male"
  },
  {
    id: "q-m3",
    aesthetic: "Classic Prep",
    description: "Ribbed cable-knit cardigan over organic Oxford buttondown, tailored chinos, leather loafers",
    imageUrl: "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&q=80&w=600",
    tags: ["classic", "collegiate", "preppy"],
    gender: "male"
  },
  {
    id: "q-m4",
    aesthetic: "Gorpcore Techwear",
    description: "Weatherproof shell-jacket, double-clip adjustable hardware tactical trousers, GORE-TEX boots",
    imageUrl: "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?auto=format&fit=crop&q=80&w=600",
    tags: ["wear-resistant", "functional", "tactical"],
    gender: "male"
  },
  {
    id: "q-m5",
    aesthetic: "Smart Tailored",
    description: "Sharp charcoal wool blazer, single-pleat dress pants, polished black Oxford shoes",
    imageUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=600",
    tags: ["tailored", "office", "sharp"],
    gender: "male"
  },
  {
    id: "q-m6",
    aesthetic: "Cyberpunk Techwear",
    description: "Dark reflective technical windbreaker with utility back pocket, black buckle straps",
    imageUrl: "https://images.unsplash.com/photo-1505022610485-0249ba5b3675?auto=format&fit=crop&q=80&w=600",
    tags: ["futuristic", "dark", "straps"],
    gender: "male"
  },
  {
    id: "q-m7",
    aesthetic: "Retro Vintage",
    description: "Chestnut heritage corduroy overshirt, washed slim denim, authentic leather Chelsea boots",
    imageUrl: "https://images.unsplash.com/photo-1537989370856-8f3b61f77459?auto=format&fit=crop&q=80&w=600",
    tags: ["retro", "vintage", "warm"],
    gender: "male"
  },
  {
    id: "q-m8",
    aesthetic: "Modern Athleisure",
    description: "Sleek zip-face performance training track jacket, high-elastic trousers, runner sneakers",
    imageUrl: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&q=80&w=600",
    tags: ["active", "sleek", "functional"],
    gender: "male"
  }
];

export const INITIAL_CLOSET_ITEMS: ClosetItem[] = [
  // --- FEMALE INVENTORY ---
  {
    id: "macy-f1",
    name: "Lauren Ralph Lauren Double-Breasted Camel Trench",
    category: "Outerwear",
    color: "Camel Beige",
    pattern: "Water-resistant woven gabardine",
    vibe: "Elegant tailored outerwear, sharp cinched waist look",
    imageUrl: "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&q=80&w=400",
    brand: "Lauren Ralph Lauren",
    gender: "female"
  },
  {
    id: "macy-f2",
    name: "Calvin Klein Silk-Blend Pleated Trousers",
    category: "Bottoms",
    color: "Slate Charcoal Grey",
    pattern: "Smooth stretch crease-front drapery",
    vibe: "Polished commuter lines, high-waisted and modern tapered fit",
    imageUrl: "https://images.unsplash.com/photo-1506629082925-0151a14e6267?auto=format&fit=crop&q=80&w=400",
    brand: "Calvin Klein",
    gender: "female"
  },
  {
    id: "macy-f3",
    name: "INC International Concepts Puff-Sleeve Sage Dress",
    category: "Tops",
    color: "Sage Floral Green",
    pattern: "Delicate daisy pattern jacquard",
    vibe: "Breezy romantic weekend look with elasticized puff sleeves",
    imageUrl: "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&q=80&w=400",
    brand: "INC International Concepts",
    gender: "female"
  },
  {
    id: "macy-f4",
    name: "Charter Club Cable-Knit Cashmere Pullover",
    category: "Tops",
    color: "Creamy Ivory",
    pattern: "Thick ribbed knit cable texture",
    vibe: "Cozy refined prep, classic warm collar layering step",
    imageUrl: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&q=80&w=400",
    brand: "Charter Club",
    gender: "female"
  },
  {
    id: "macy-f5",
    name: "Michael Kors Suede Pointed Slingback Heels",
    category: "Shoes",
    color: "Earthy Chestnut",
    pattern: "Rich velvety heavy duty suede",
    vibe: "Elegant footwear accent for cocktail and upscale smart events",
    imageUrl: "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&q=80&w=400",
    brand: "Michael Kors",
    gender: "female"
  },
  {
    id: "macy-f6",
    name: "Coach Leather Signature Monogram Belt",
    category: "Accessories",
    color: "Rich Cognac Brown",
    pattern: "Classic embossed pebble leather",
    vibe: "Sleek hardware detailing to anchor loose-fit dresses or denim",
    imageUrl: "https://images.unsplash.com/photo-1624222247344-550fb80f02d4?auto=format&fit=crop&q=80&w=400",
    brand: "Coach",
    gender: "female"
  },

  // --- MALE INVENTORY ---
  {
    id: "macy-m1",
    name: "Club Room Merino Wool Crewneck",
    category: "Tops",
    color: "Navy Blue",
    pattern: "Fine gauge soft flat knit",
    vibe: "Understated luxury, comfortable tailored daily layer",
    imageUrl: "https://images.unsplash.com/photo-1516257984-b1b4d707412e?auto=format&fit=crop&q=80&w=400",
    brand: "Club Room",
    gender: "male"
  },
  {
    id: "macy-m2",
    name: "Polo Ralph Lauren Oxford Cotton Button-Down",
    category: "Tops",
    color: "Sky Blue",
    pattern: "Crisp breathable oxford weave",
    vibe: "Classic Ivy collegiate smart casual wardrobe standard",
    imageUrl: "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&q=80&w=400",
    brand: "Polo Ralph Lauren",
    gender: "male"
  },
  {
    id: "macy-m3",
    name: "Levi's 511 Slim Fit Stretch Denim Jeans",
    category: "Bottoms",
    color: "Dark Indigo Wash",
    pattern: "Raw textured denim twill",
    vibe: "Rugged yet modern semi-structured lower layer coordinates",
    imageUrl: "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&q=80&w=400",
    brand: "Levi's",
    gender: "male"
  },
  {
    id: "macy-m4",
    name: "Calvin Klein Modern Wool Sport Coat",
    category: "Outerwear",
    color: "Charcoal Grey Tweed",
    pattern: "Fine-textured weave herringbone",
    vibe: "Sharp structured shoulder drape for boardrooms or dinner dates",
    imageUrl: "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&q=80&w=400",
    brand: "Calvin Klein",
    gender: "male"
  },
  {
    id: "macy-m5",
    name: "Alfani Premium Calfskin Leather Loafers",
    category: "Shoes",
    color: "Polished Tuxedo Black",
    pattern: "Mirror shine slip-on dress leather",
    vibe: "Durable traction, comfortable fit with high-end shoe silhouette",
    imageUrl: "https://images.unsplash.com/photo-1533867617858-e7b97e060509?auto=format&fit=crop&q=80&w=400",
    brand: "Alfani",
    gender: "male"
  },
  {
    id: "macy-m6",
    name: "Tommy Hilfiger Sport Tech Windbreaker",
    category: "Outerwear",
    color: "Matte Black",
    pattern: "Waterproof lightweight nylon fabric",
    vibe: "Active sport aesthetic protective shell, tech hardware accents",
    imageUrl: "https://images.unsplash.com/photo-1505022610485-0249ba5b3675?auto=format&fit=crop&q=80&w=400",
    brand: "Tommy Hilfiger",
    gender: "male"
  }
];
