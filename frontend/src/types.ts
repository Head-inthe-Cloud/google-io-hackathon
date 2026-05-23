export type GarmentCategory = "Tops" | "Bottoms" | "Outerwear" | "Shoes" | "Accessories";

export interface StylePreference {
  id: string;
  name: string;
  chineseName: string;
  description: string;
  vibeText: string;
  imageUrl: string;
}

export interface ClosetItem {
  id: string;
  name: string;
  category: GarmentCategory;
  color: string;
  pattern: string;
  vibe: string;
  imageUrl?: string;
  isCustom?: boolean;
  brand?: string;
  gender?: "male" | "female" | "unisex";
}

export interface SourcedProduct {
  name: string;
  price: string;
  reason: string;
}

export interface OutfitRecommendation {
  outfitName: string;
  rationale: string;
  items: Array<{
    id: string;
    name: string;
    category: GarmentCategory;
  }>;
  onlineSourced: SourcedProduct[];
  tryOnAdvice: string;
}

export interface UserPortfolio {
  selectedStyles: string[]; // style IDs
  selfieImage: string | null; // Base64
  selfieDescription: string;
  lovedOutfits: Array<{
    id: string;
    outfitName: string;
    rationale: string;
    items: string[]; // item names
    onlineSourced: SourcedProduct[];
    tryOnAdvice: string;
    likedAt: string;
  }>;
}
