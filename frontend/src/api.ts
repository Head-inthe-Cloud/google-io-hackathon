/**
 * API Service Layer — connects the frontend to the FastAPI backend.
 *
 * All backend calls are routed through `/api/*` which is proxied
 * to the FastAPI backend (default: http://localhost:8000) via Vite's
 * dev proxy or the Express server's proxy in production.
 */

import type { ClosetItem, GarmentCategory, OutfitRecommendation, SourcedProduct } from "./types";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const API_BASE = ""; // Relative — goes through the proxy

// ---------------------------------------------------------------------------
// Catalog
// ---------------------------------------------------------------------------
export interface CatalogFilters {
  gender?: string;       // "mens" | "womens"
  category?: string;
  search?: string;
  color?: string;
  activity?: string;
  collection?: string;
  limit?: number;
  offset?: number;
}

export interface CatalogResponse {
  total: number;
  count: number;
  offset: number;
  limit: number;
  items: BackendCatalogItem[];
}

export interface BackendCatalogItem {
  id: number;
  name: string;
  image_url: string;
  imageUrl: string;
  description: string | null;
  vibe: string | null;
  category: string;
  gender: string;
  color: string | null;
  colors: string[] | null;
  pattern: string | null;
  fit: string | null;
  activity: string | null;
  collection: string | null;
  product_link: string | null;
  style_tags: string[] | null;
  brand: string;
}

/** Map a backend catalog item to the frontend ClosetItem format. */
export function catalogItemToClosetItem(item: BackendCatalogItem): ClosetItem {
  const normalizedCategory = (item.category || "").toLowerCase();

  // Map backend categories to frontend GarmentCategory
  const categoryMap: Record<string, GarmentCategory> = {
    "Tops": "Tops",
    "tops": "Tops",
    "knit tops": "Tops",
    "wovens": "Tops",
    "t shirt": "Tops",
    "Bottoms": "Bottoms",
    "bottoms": "Bottoms",
    "pants": "Bottoms",
    "jeans": "Bottoms",
    "shorts": "Bottoms",
    "skirt": "Bottoms",
    "Outerwear": "Outerwear",
    "outerwear": "Outerwear",
    "jacket": "Outerwear",
    "coat": "Outerwear",
    "Sports Bras": "Tops",       // Map to closest frontend category
    "Accessories": "Accessories",
    "accessories": "Accessories",
    "Shoes": "Shoes",
    "shoes": "Shoes",
    "One-Piece": "Tops",         // Map to closest frontend category
  };
  const mappedCategory = categoryMap[item.category] || categoryMap[normalizedCategory] || "Tops";

  // Map backend gender to frontend gender
  const genderMap: Record<string, "male" | "female" | "unisex"> = {
    "mens": "male",
    "men": "male",
    "male": "male",
    "womens": "female",
    "women": "female",
    "female": "female",
    "unisex": "unisex",
  };

  return {
    id: `catalog-${item.id}`,
    name: item.name,
    category: mappedCategory,
    color: item.color || "Unknown",
    pattern: item.pattern || item.fit || "Standard",
    vibe: item.description || item.vibe || "A stylish garment.",
    imageUrl: item.image_url || item.imageUrl,
    productLink: item.product_link || undefined,
    isCustom: false,
    brand: item.brand || "Gymshark",
    gender: genderMap[item.gender] || "unisex",
  };
}

/** Fetch catalog items with filtering and pagination. */
export async function fetchCatalog(filters: CatalogFilters = {}): Promise<CatalogResponse> {
  const params = new URLSearchParams();
  if (filters.gender) params.set("gender", filters.gender);
  if (filters.category) params.set("category", filters.category);
  if (filters.search) params.set("search", filters.search);
  if (filters.color) params.set("color", filters.color);
  if (filters.activity) params.set("activity", filters.activity);
  if (filters.collection) params.set("collection", filters.collection);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));

  const res = await fetch(`${API_BASE}/api/catalog?${params.toString()}`);
  if (!res.ok) throw new Error(`Catalog fetch failed: ${res.status}`);
  return res.json();
}

/** Fetch category counts. */
export async function fetchCategories(): Promise<Record<string, number>> {
  const res = await fetch(`${API_BASE}/api/catalog/categories`);
  if (!res.ok) throw new Error(`Categories fetch failed: ${res.status}`);
  const data = await res.json();
  return data.categories;
}

/** Fetch a single catalog item. */
export async function fetchCatalogItem(itemId: number): Promise<BackendCatalogItem> {
  const res = await fetch(`${API_BASE}/api/catalog/${itemId}`);
  if (!res.ok) throw new Error(`Catalog item fetch failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Advanced Catalog Search Tree & Facets
// ---------------------------------------------------------------------------
export interface SearchTreeResponse {
  total_products: number;
  navigation_order: string[];
  navigation_tree: NavigationNode[];
  facet_fields: string[];
  facets: Record<string, FacetItem[]>;
}

export interface NavigationNode {
  field: string;
  value: string;
  label: string;
  count: number;
  children?: NavigationNode[];
}

export interface FacetItem {
  value: string;
  label: string;
  count: number;
}

/** Fetch catalog search tree. Supports dataset: 'current' | 'dataset2' | 'gymshark' */
export async function fetchCatalogSearchTree(dataset = "current"): Promise<SearchTreeResponse> {
  const res = await fetch(`${API_BASE}/api/catalog/search-tree?dataset=${dataset}`);
  if (!res.ok) throw new Error(`Search tree fetch failed: ${res.status}`);
  return res.json();
}

/** Fetch catalog facets. Supports dataset: 'current' | 'dataset2' | 'gymshark' */
export async function fetchCatalogFacets(dataset = "current"): Promise<Record<string, FacetItem[]>> {
  const res = await fetch(`${API_BASE}/api/catalog/facets?dataset=${dataset}`);
  if (!res.ok) throw new Error(`Facets fetch failed: ${res.status}`);
  const data = await res.json();
  return data.facets;
}

/** Fetch catalog hierarchical navigation tree. Supports dataset: 'current' | 'dataset2' | 'gymshark' */
export async function fetchCatalogNavigation(dataset = "current"): Promise<{ navigation_order: string[]; navigation_tree: NavigationNode[] }> {
  const res = await fetch(`${API_BASE}/api/catalog/navigation?dataset=${dataset}`);
  if (!res.ok) throw new Error(`Navigation fetch failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Analyze Item (Gemini Vision)
// ---------------------------------------------------------------------------
export interface AnalyzeItemResult {
  id: string;
  name: string;
  category: string;
  color: string;
  pattern: string;
  vibe: string;
  isMock: boolean;
}

export async function analyzeItem(imageBase64: string, filename?: string): Promise<AnalyzeItemResult> {
  const res = await fetch(`${API_BASE}/api/analyze-item`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageBase64, filename }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(err.detail || err.error || "Analysis failed");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------
export interface RecommendParams {
  preferences?: string[];
  closet?: ClosetItem[];
  selfieDescription?: string;
  selfieImage?: string | null;
  prompt?: string;
  inspirationImage?: string | null;
  styleVector?: number[];
  preferenceProfile?: string;
  gender?: string;
}

export interface RecommendationTraceStep {
  label: string;
  detail: string;
  status?: "active" | "complete" | "error";
}

export interface RecommendResponse {
  recommendations: OutfitRecommendation[];
  traceStack?: RecommendationTraceStep[];
}

export async function getRecommendations(params: RecommendParams): Promise<RecommendResponse> {
  const body: any = {
    preferences: params.preferences || [],
    selfieDescription: params.selfieDescription || "Average build, neutral undertone",
    prompt: params.prompt || "A stylish casual look",
    styleVector: params.styleVector || [],
    preferenceProfile: params.preferenceProfile,
    gender: params.gender,
  };

  // Send closet items if provided
  if (params.closet && params.closet.length > 0) {
    body.closet = params.closet.map(item => ({
      id: item.id,
      name: item.name,
      category: item.category,
      color: item.color,
      pattern: item.pattern,
      vibe: item.vibe,
      description: item.vibe,
      imageUrl: item.imageUrl,
      productLink: item.productLink,
      brand: item.brand,
    }));
  }

  if (params.inspirationImage) {
    body.inspirationImage = params.inspirationImage;
  }

  const res = await fetch(`${API_BASE}/api/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Recommendation failed" }));
    throw new Error(err.detail || "Recommendation failed");
  }
  return res.json();
}

export interface PreferenceProfileParams {
  preferences?: string[];
  likedQuizOutfits?: Array<{
    id: string;
    aesthetic: string;
    description: string;
    imageUrl: string;
    tags: string[];
    gender: string;
  }>;
  selfieDescription?: string;
  selfieImage?: string | null;
  prompt?: string;
  inspirationImage?: string | null;
  styleVector?: number[];
  gender?: string;
}

export interface PreferenceProfileResponse {
  preferenceProfile: string;
  profileTags?: string[];
  avoid?: string[];
  confidence?: number;
  source?: string;
}

export async function buildPreferenceProfile(params: PreferenceProfileParams): Promise<PreferenceProfileResponse> {
  const res = await fetch(`${API_BASE}/api/preference-profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Preference profile generation failed" }));
    throw new Error(err.detail || "Preference profile generation failed");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Virtual Try-On (Replicate-based)
// ---------------------------------------------------------------------------
export interface TryOnResult {
  status: string;
  replicate_id?: string;
  output_url?: string;
  message?: string;
}

export async function triggerVirtualTryOn(selfieUrl: string, garmentUrl: string): Promise<TryOnResult> {
  const res = await fetch(`${API_BASE}/api/virtual-try-on`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selfie_url: selfieUrl, garment_url: garmentUrl }),
  });
  if (!res.ok) throw new Error(`Try-on trigger failed: ${res.status}`);
  return res.json();
}

export async function checkTryOnStatus(predictionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/virtual-try-on/status/${predictionId}`);
  if (!res.ok) throw new Error(`Try-on status check failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Synthetic Try-On Image Generation (Gemini)
// ---------------------------------------------------------------------------
export interface GenerateTryOnParams {
  outfitName?: string;
  prompt?: string;
  itemsStr?: string;
  items?: Array<{
    id?: string;
    name?: string;
    category?: string;
    color?: string;
    brand?: string;
    imageUrl?: string;
  }>;
  itemImages?: string[];
  selfieBase64?: string | null;
  variants?: number;
}

export interface TryOnGuardrail {
  status?: "checked" | "skipped" | "error";
  pass?: boolean | null;
  faithfulness_score?: number | null;
  issues?: string[];
  dimension_scores?: Record<string, number>;
}

export interface GenerateTryOnResult {
  imageUrl?: string;
  simulatedUrl?: string;
  advice?: string;
  source?: string;
  guardrail?: TryOnGuardrail;
  garmentReferenceCount?: number;
  recommendedItemsUsed?: string[];
  selectedVariantIndex?: number;
  variantCount?: number;
  variantScores?: Array<{
    variantIndex: number;
    pass?: boolean | null;
    faithfulness_score?: number | null;
    status?: string;
    issues?: string[];
  }>;
  error?: string;
}

export async function generateTryOnImage(params: GenerateTryOnParams): Promise<GenerateTryOnResult> {
  const res = await fetch(`${API_BASE}/api/generate-try-on`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Generation failed" }));
    throw new Error(err.detail || err.error || "Generation failed");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Sessions (optional — for persistent session management)
// ---------------------------------------------------------------------------
export interface CreateSessionParams {
  selfie_url?: string;
  gender_preference?: string;
  favorite_colors?: string[];
  disliked_styles?: string[];
  occasion?: string;
  notes?: string;
}

export async function createSession(params: CreateSessionParams = {}): Promise<{ session_id: number; session_token: string }> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Session creation failed: ${res.status}`);
  return res.json();
}

export async function getSession(token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/sessions/${token}`);
  if (!res.ok) throw new Error(`Session fetch failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Upload URL (S3 presigned)
// ---------------------------------------------------------------------------
export async function getUploadUrl(filename: string): Promise<{ upload_url: string; file_url: string }> {
  const res = await fetch(`${API_BASE}/api/upload-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename }),
  });
  if (!res.ok) throw new Error(`Upload URL generation failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Health Check
// ---------------------------------------------------------------------------
export async function checkHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
