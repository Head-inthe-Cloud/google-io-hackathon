import { useState, useEffect, useRef, useCallback, ChangeEvent } from "react";
import { 
  Sparkles, 
  Upload, 
  Trash2, 
  Heart, 
  RotateCcw, 
  ChevronRight, 
  ThumbsUp, 
  ThumbsDown, 
  FileText, 
  Layers, 
  User, 
  Check, 
  Shirt, 
  ShoppingBag, 
  Plus, 
  HelpCircle, 
  Info, 
  Image as ImageIcon,
  Flame,
  FileCheck2,
  Cpu,
  Search,
  SlidersHorizontal,
  Globe,
  Terminal,
  Network
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { STYLE_PREF_CHOICES, INITIAL_CLOSET_ITEMS, STYLE_QUIZ_OUTFITS, QuizOutfit } from "./data";
import { ClosetItem, StylePreference, OutfitRecommendation, UserPortfolio, GarmentCategory, SourcedProduct } from "./types";
import * as api from "./api";

type RecommendationTraceStep = api.RecommendationTraceStep;

const policyLinesFromProfile = (profile: string) =>
  profile
    .split(/\n+/)
    .map((line) => line.replace(/^[-•]\s*/, "").trim())
    .filter(Boolean);

function PreferencePolicyPanel({ profile }: { profile: string }) {
  const lines = policyLinesFromProfile(profile);
  if (lines.length === 0) return null;

  return (
    <div className="border border-neutral-850 bg-neutral-900/35 rounded-2xl p-4">
      <div className="flex items-center space-x-2 mb-3">
        <FileCheck2 className="w-4 h-4 text-amber-200" />
        <h3 className="text-[11px] font-mono uppercase tracking-wider text-neutral-200">Preference Policy</h3>
      </div>
      <ul className="space-y-2">
        {lines.map((line, index) => (
          <li key={`${line}-${index}`} className="flex gap-2 text-xs leading-relaxed text-neutral-300">
            <Check className="w-3.5 h-3.5 text-emerald-300 mt-0.5 flex-shrink-0" />
            <span>{line}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TraceStackPanel({ steps }: { steps: RecommendationTraceStep[] }) {
  if (steps.length === 0) return null;

  return (
    <div className="border border-neutral-850 bg-neutral-950/45 rounded-2xl p-4">
      <div className="flex items-center space-x-2 mb-3">
        <Terminal className="w-4 h-4 text-neutral-300" />
        <h3 className="text-[11px] font-mono uppercase tracking-wider text-neutral-200">Recommendation Trace</h3>
      </div>
      <ol className="space-y-2">
        {steps.map((step, index) => (
          <li key={`${step.label}-${index}`} className="grid grid-cols-[18px_1fr] gap-2 text-xs">
            <span
              className={`mt-1 h-2.5 w-2.5 rounded-full ${
                step.status === "error"
                  ? "bg-rose-400"
                  : step.status === "active"
                    ? "bg-amber-200 animate-pulse"
                    : "bg-emerald-300"
              }`}
            />
            <span>
              <span className="block text-neutral-100">{step.label}</span>
              <span className="block text-neutral-450 leading-relaxed">{step.detail}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function GuardrailPanel({ guardrail }: { guardrail: api.TryOnGuardrail | null }) {
  if (!guardrail) return null;

  const status =
    guardrail.status === "checked"
      ? guardrail.pass
        ? "Passed"
        : "Needs review"
      : guardrail.status === "error"
        ? "Error"
        : "Skipped";

  return (
    <div className="mt-3 border border-neutral-850 bg-neutral-950/70 rounded-xl p-3 text-left">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400">Image Guardrail</span>
        <span className="text-[10px] font-mono text-neutral-200">{status}</span>
      </div>
      {typeof guardrail.faithfulness_score === "number" && (
        <p className="text-[11px] text-neutral-300 mb-1">
          Faithfulness score: {guardrail.faithfulness_score.toFixed(2)}
        </p>
      )}
      {guardrail.issues && guardrail.issues.length > 0 && (
        <p className="text-[11px] text-neutral-450 leading-relaxed">{guardrail.issues.join("; ")}</p>
      )}
    </div>
  );
}

const AESTHETIC_FACTORS: Record<string, number[]> = {
  "Minimalist": [1.0, -0.6, 0.2, -0.8, -0.2, -1.0, -0.8, 0.4],
  "Streetwear": [-0.6, -1.0, 0.8, 0.4, -0.1, 0.6, 0.9, 0.2],
  "Classic Prep / Academic": [0.4, 0.6, -0.8, -0.6, 0.4, -0.4, -0.9, -0.4],
  "Y2K Retro": [-0.8, -0.8, 0.9, -0.4, -0.2, 1.0, 0.7, 0.8],
  "Cottagecore / Romantic": [-0.5, -0.8, -0.9, -0.8, 0.8, 0.3, -0.5, -0.9],
  "Athleisure": [0.6, -0.9, 0.5, 0.9, -0.4, 0.2, -0.2, 0.9],
  "Business Casual": [0.8, 0.9, -0.2, -0.6, 0.1, -0.8, -0.6, 0.1],
  "Old-Money Luxury": [0.9, 0.8, -0.7, -0.7, 0.5, -0.9, -0.9, -0.5],
  "Grunge & Edge": [-0.8, -0.9, -0.4, 0.2, -0.6, -0.5, 1.0, -0.2],
  "Bohemian / Free Spirit": [-0.9, -0.9, -0.8, -0.5, 0.9, 0.8, 0.5, -0.9],
  "Gorpcore": [0.1, -0.7, 0.6, 1.0, -0.5, -0.3, 0.4, 1.0],
  "Quiet Luxury": [1.0, 0.9, -0.5, -0.8, 0.3, -1.0, -0.8, -0.3],
  "Cyberpunk / Techwear": [-0.7, -0.6, 1.0, 0.8, -0.8, 0.5, 0.9, 1.0],
  "Coastal Grandmother": [0.8, -0.5, -0.6, -0.8, 0.6, -0.9, -0.8, -0.6]
};

const DIMENSION_LABELS = [
  "Minimalist vs Ornamental",
  "Casual vs Structured",
  "Heritage vs Futuristic",
  "Active/Utility vs Leisure",
  "Vibrant vs Monochrome",
  "Retro vs High-Tech",
  "Understated vs Edgy",
  "Organic vs Synthetic"
];

const DEFAULT_SELECTED_STYLE_IDS = ["minimalist", "preppy"];

const AESTHETIC_ALIASES: Record<string, string> = {
  "Minimalist Casual": "Minimalist",
  "Streetwear Grunge": "Streetwear",
  "Classic Prep": "Classic Prep / Academic",
  "Cottagecore Romantic": "Cottagecore / Romantic",
  "Athleisure Active": "Athleisure",
  "Smart Executive": "Business Casual",
  "Bohemian Artisanal": "Bohemian / Free Spirit",
  "Gorpcore Techwear": "Gorpcore",
  "Smart Tailored": "Business Casual",
  "Retro Vintage": "Y2K Retro",
  "Modern Athleisure": "Athleisure",
};

export default function App() {
  // Navigation Tabs
  const [activeTab, setActiveTab] = useState<"discover" | "closet" | "liked" | "designdoc">("discover");

  // Onboarding state
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState<boolean>(() => {
    return localStorage.getItem("closet_onboarding") === "true";
  });
  const [selectedStylesOnboard, setSelectedStylesOnboard] = useState<string[]>(() => {
    const saved = localStorage.getItem("user_selected_style_ids");
    return saved ? JSON.parse(saved) : DEFAULT_SELECTED_STYLE_IDS;
  });
  const [selfieTraitsInput, setSelfieTraitsInput] = useState<string>("Slightly warm undertones, standard slim frame, light chestnut hair.");

  // Style Preference Quiz states
  const [likedQuizOutfits, setLikedQuizOutfits] = useState<string[]>(() => {
    const saved = localStorage.getItem("user_liked_quiz_outfits");
    return saved ? JSON.parse(saved) : [];
  });
  
  const [userStyleVector, setUserStyleVector] = useState<number[]>(() => {
    const saved = localStorage.getItem("user_style_vector");
    if (saved) return JSON.parse(saved);
    // Initial balanced style DNA vector
    return [0.15, -0.22, 0.45, 0.61, -0.12, -0.35, 0.28, -0.05];
  });

  const [quizGender, setQuizGender] = useState<"female" | "male">(() => {
    return (localStorage.getItem("user_quiz_gender") as "female" | "male") || "female";
  });

  const [onboardingStep, setOnboardingStep] = useState<number>(1);

  // General state
  const [closetItems, setClosetItems] = useState<ClosetItem[]>([]);

  // Backend catalog loading state
  const [catalogTotal, setCatalogTotal] = useState<number>(0);
  const [isCatalogLoading, setIsCatalogLoading] = useState<boolean>(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

  const [selfieImage, setSelfieImage] = useState<string | null>(() => {
    return localStorage.getItem("user_selfie") || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=600";
  });

  const [selfieDescription, setSelfieDescription] = useState<string>(() => {
    return localStorage.getItem("user_selfie_desc") || "Subtle golden undertones, medium build, suited for layered structural apparel.";
  });

  const [likedOutfits, setLikedOutfits] = useState<UserPortfolio["lovedOutfits"]>(() => {
    const saved = localStorage.getItem("user_liked_outfits");
    return saved ? JSON.parse(saved) : [];
  });

  // Query generation state
  const [userPrompt, setUserPrompt] = useState<string>("");
  const [inspirationImage, setInspirationImage] = useState<string | null>(null);
  const [isRecommending, setIsRecommending] = useState<boolean>(false);
  const [recsQueue, setRecsQueue] = useState<OutfitRecommendation[]>([]);
  const [queueIndex, setQueueIndex] = useState<number>(0);
  const [likedRecFeedback, setLikedRecFeedback] = useState<boolean>(false);
  const [preferenceProfile, setPreferenceProfile] = useState<string>(() => {
    return localStorage.getItem("user_preference_profile") || "";
  });
  const [recommendationTraceStack, setRecommendationTraceStack] = useState<RecommendationTraceStep[]>([]);

  // Clothing item analysis state
  const [isAnalyzingItem, setIsAnalyzingItem] = useState<boolean>(false);
  const [analyzingSuccess, setAnalyzingSuccess] = useState<string | null>(null);

  // Macy's Store Stock filtering states
  const [storeGenderFilter, setStoreGenderFilter] = useState<"all" | "male" | "female">("all");
  const [storeCategoryFilter, setStoreCategoryFilter] = useState<"all" | GarmentCategory>("all");
  const [storeSearchQuery, setStoreSearchQuery] = useState<string>("");
  const [stockroomItems, setStockroomItems] = useState<ClosetItem[]>([]);
  const [stockroomTotal, setStockroomTotal] = useState<number>(0);
  const [isStockroomLoading, setIsStockroomLoading] = useState<boolean>(false);
  const [stockroomError, setStockroomError] = useState<string | null>(null);

  // Advanced Visual Try-on simulation state
  const [isGeneratingVisual, setIsGeneratingVisual] = useState<boolean>(false);
  const [generatedVisualUrl, setGeneratedVisualUrl] = useState<string | null>(null);
  const [visualError, setVisualError] = useState<string | null>(null);
  const [visualGuardrail, setVisualGuardrail] = useState<api.TryOnGuardrail | null>(null);
  const autoTryOnKeyRef = useRef<string>("");

  // Save states to LocalStorage
  // Load catalog from backend on mount (and when gender changes)
  useEffect(() => {
    let cancelled = false;
    async function loadCatalog() {
      setIsCatalogLoading(true);
      setCatalogError(null);
      try {
        // Check if backend is up
        const healthRes = await fetch("/api/health").then(r => r.json()).catch(() => null);
        if (!healthRes || healthRes.status !== "ok") {
          console.warn("Backend not reachable, using local fallback data.");
          setBackendConnected(false);
          // Fall back to hardcoded mock items only when backend is down
          setClosetItems(prev => prev.length === 0 ? INITIAL_CLOSET_ITEMS : prev);
          setIsCatalogLoading(false);
          return;
        }
        setBackendConnected(true);

        // Load catalog items from backend
        const genderPref = quizGender === "male" ? "mens" : "womens";
        const data = await api.fetchCatalog({ gender: genderPref, limit: 50 });
        if (cancelled) return;
        setCatalogTotal(data.total);

        // Backend items replace all non-custom items
        const backendItems = data.items.map(api.catalogItemToClosetItem);
        setClosetItems(prev => {
          const customItems = prev.filter(i => i.isCustom);
          return [...customItems, ...backendItems];
        });
      } catch (err: any) {
        console.warn("Failed to load catalog from backend:", err.message);
        setBackendConnected(false);
        setCatalogError(err.message);
        // Fall back to hardcoded mock items
        setClosetItems(prev => prev.length === 0 ? INITIAL_CLOSET_ITEMS : prev);
      } finally {
        if (!cancelled) setIsCatalogLoading(false);
      }
    }
    loadCatalog();
    return () => { cancelled = true; };
  }, [quizGender]);

  useEffect(() => {
    if (selfieImage) localStorage.setItem("user_selfie", selfieImage);
  }, [selfieImage]);

  useEffect(() => {
    localStorage.setItem("user_selfie_desc", selfieDescription);
  }, [selfieDescription]);

  useEffect(() => {
    localStorage.setItem("user_liked_outfits", JSON.stringify(likedOutfits));
  }, [likedOutfits]);

  useEffect(() => {
    localStorage.setItem("user_selected_style_ids", JSON.stringify(selectedStylesOnboard));
  }, [selectedStylesOnboard]);

  useEffect(() => {
    localStorage.setItem("user_preference_profile", preferenceProfile);
  }, [preferenceProfile]);

  // Save Style Preference Quiz states
  useEffect(() => {
    localStorage.setItem("user_liked_quiz_outfits", JSON.stringify(likedQuizOutfits));
  }, [likedQuizOutfits]);

  useEffect(() => {
    localStorage.setItem("user_style_vector", JSON.stringify(userStyleVector));
  }, [userStyleVector]);

  useEffect(() => {
    let cancelled = false;
    async function loadStockroom() {
      if (!backendConnected) return;
      setIsStockroomLoading(true);
      setStockroomError(null);
      try {
        const gender =
          storeGenderFilter === "male"
            ? "mens"
            : storeGenderFilter === "female"
              ? "womens"
              : undefined;
        const data = await api.fetchCatalog({
          gender,
          category: storeCategoryFilter === "all" ? undefined : storeCategoryFilter,
          search: storeSearchQuery.trim() || undefined,
          limit: 120,
        });
        if (cancelled) return;
        setStockroomTotal(data.total);
        setStockroomItems(data.items.map(api.catalogItemToClosetItem));
      } catch (err: any) {
        if (cancelled) return;
        setStockroomError(err.message || String(err));
      } finally {
        if (!cancelled) setIsStockroomLoading(false);
      }
    }
    loadStockroom();
    return () => { cancelled = true; };
  }, [backendConnected, storeGenderFilter, storeCategoryFilter, storeSearchQuery]);

  // Toggle quiz selections & calculate live vector values using the factors matrix
  const handleToggleQuizOutfit = (id: string) => {
    setLikedQuizOutfits((prev) => {
      const next = prev.includes(id) ? prev.filter((oId) => oId !== id) : [...prev, id];
      const computedVector = recalculateStyleVector(next);
      setUserStyleVector(computedVector);
      return next;
    });
  };

  const recalculateStyleVector = (likedIds: string[]) => {
    if (likedIds.length === 0) {
      return [0.15, -0.22, 0.45, 0.61, -0.12, -0.35, 0.28, -0.05];
    }
    
    const sumVector = Array(8).fill(0);
    likedIds.forEach(id => {
      const outfit = STYLE_QUIZ_OUTFITS.find(o => o.id === id);
      const factorKey = outfit ? AESTHETIC_ALIASES[outfit.aesthetic] || outfit.aesthetic : "";
      if (factorKey && AESTHETIC_FACTORS[factorKey]) {
        const factors = AESTHETIC_FACTORS[factorKey];
        for (let i = 0; i < 8; i++) {
          sumVector[i] += factors[i];
        }
      }
    });

    const norm = Math.sqrt(sumVector.reduce((sum, val) => sum + val * val, 0)) || 1;
    return sumVector.map(val => parseFloat((val / norm).toFixed(3)));
  };

  // Handle onboarding submission
  const handleCompleteOnboarding = () => {
    localStorage.setItem("closet_onboarding", "true");
    setHasCompletedOnboarding(true);
    // Switch to discover
    setActiveTab("discover");
  };

  const resetOnboarding = () => {
    localStorage.removeItem("closet_onboarding");
    setHasCompletedOnboarding(false);
  };

  const upsertRecommendationTrace = useCallback((step: RecommendationTraceStep) => {
    setRecommendationTraceStack((prev) => {
      const existingIndex = prev.findIndex((item) => item.label === step.label);
      if (existingIndex === -1) return [...prev, step];
      return prev.map((item, index) => (index === existingIndex ? step : item));
    });
  }, []);

  // 1-Click test image loader for items
  const addPresetItem = (preset: { name: string; category: GarmentCategory; color: string; pattern: string; vibe: string; image: string }) => {
    const newItem: ClosetItem = {
      id: `preset-${Date.now()}`,
      name: preset.name,
      category: preset.category,
      color: preset.color,
      pattern: preset.pattern,
      vibe: preset.vibe,
      imageUrl: preset.image,
      isCustom: true
    };
    setClosetItems((prev) => [newItem, ...prev]);
    setAnalyzingSuccess(`Added "${preset.name}" effortlessly to your closet!`);
    setTimeout(() => setAnalyzingSuccess(null), 3500);
  };

  // Macy's Live Web Scraper state management
  const [scraperMode, setScraperMode] = useState<"search" | "url">("search");
  const [scraperQuery, setScraperQuery] = useState<string>("mens outerwear blazers");
  const [scraperUrl, setScraperUrl] = useState<string>("https://www.macys.com/shop/product/calvin-klein-mens-infinite-stretch-blazer");
  const [isScraping, setIsScraping] = useState<boolean>(false);
  const [scraperLogs, setScraperLogs] = useState<string[]>([
    "System Idle. Scraper engine online.",
    "Select Search-Grounded Crawler or Custom URL Crawler to begin ingesting products."
  ]);
  const [scraperSuccessMsg, setScraperSuccessMsg] = useState<string | null>(null);

  // Trigger scraper call to the Express backend
  const handleRunScraper = async () => {
    setIsScraping(true);
    setScraperSuccessMsg(null);
    setScraperLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] Establishing secure crawling socket...`,
      scraperMode === "search" 
        ? `[Request] Dispatched Google Search-Grounded Scraper query: "${scraperQuery}"` 
        : `[Request] Initiated HTML structure scan for URL: "${scraperUrl}"`
    ]);

    try {
      const genderPref = quizGender === "male" ? "mens" : "womens";
      const data = await api.fetchCatalog({
        search: scraperMode === "search" ? scraperQuery : undefined,
        gender: genderPref,
        limit: 20,
      });

      setScraperLogs((prev) => [
        ...prev,
        `[catalog] Backend returned ${data.count} items (${data.total} total matching).`
      ]);

      if (data.items.length > 0) {
        const newItems = data.items.map(api.catalogItemToClosetItem);
        setClosetItems((prev) => {
          const existingIds = new Set(prev.map((item) => item.id));
          const novelOnly = newItems.filter((item) => !existingIds.has(item.id));
          if (novelOnly.length === 0) {
            setScraperLogs((prevLogs) => [
              ...prevLogs,
              `[catalog] All items already in stockroom. Deduplication completed.`
            ]);
            return prev;
          }
          return [...novelOnly, ...prev];
        });

        const existingIdSet = new Set(closetItems.map(c => c.id));
        const novelCount = newItems.filter(i => !existingIdSet.has(i.id)).length;
        setScraperSuccessMsg(`Successfully scraped ${data.count} items from Amazon! Added ${novelCount} new garments.`);
        setScraperLogs((prev) => [
          ...prev,
          `[success] Ingest pipeline synced. Stock Room expanded by ${novelCount} unique SKU configurations.`
        ]);
      } else {
        setScraperLogs((prev) => [
          ...prev,
          `[info] No items found matching "${scraperMode === "search" ? scraperQuery : scraperUrl}". Try different search terms.`
        ]);
      }
    } catch (err: any) {
      console.error("Catalog search failed:", err);
      setScraperLogs((prev) => [
        ...prev,
        `[critical] Parse failure: ${err.message || err}`
      ]);
    } finally {
      setIsScraping(false);
    }
  };

  // Convert files to base64
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>, type: "closet" | "selfie" | "inspiration") => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64String = reader.result as string;
      if (type === "selfie") {
        setSelfieImage(base64String);
      } else if (type === "inspiration") {
        setInspirationImage(base64String);
      } else if (type === "closet") {
        // Run AI Tagging on backend
        setIsAnalyzingItem(true);
        setAnalyzingSuccess(null);
        try {
          const data = await api.analyzeItem(base64String, file.name);
          const newlyTaggedGarment: ClosetItem = {
            id: data.id,
            name: data.name,
            category: data.category as GarmentCategory,
            color: data.color,
            pattern: data.pattern,
            vibe: data.vibe,
            imageUrl: base64String,
            isCustom: true,
            brand: "Custom Upload",
            gender: "unisex",
          };
          setClosetItems((prev) => [newlyTaggedGarment, ...prev]);
          setAnalyzingSuccess(`Successfully analyzed! Tagged as "${data.name}" (${data.category})`);
        } catch (err: any) {
          console.error("AI tagging failed, falling back locally:", err);
          // Local basic identification fallback
          const defaultName = file.name.split(".")[0].replace(/[-_]/g, " ");
          const localFallback: ClosetItem = {
            id: `item-${Date.now()}`,
            name: defaultName.charAt(0).toUpperCase() + defaultName.slice(1),
            category: "Tops",
            color: "Spotted Hue",
            pattern: "Woven knit",
            vibe: "A neat layering addition suited for casual everyday style.",
            imageUrl: base64String,
            isCustom: true
          };
          setClosetItems((prev) => [localFallback, ...prev]);
          setAnalyzingSuccess(`Added "${localFallback.name}" via modern offline mode.`);
        } finally {
          setIsAnalyzingItem(false);
          setTimeout(() => setAnalyzingSuccess(null), 3500);
        }
      }
    };
    reader.readAsDataURL(file);
  };

  // Request styling recommendations
  const requestStylingRecommendations = async () => {
    const activePreferences = STYLE_PREF_CHOICES.filter(p => selectedStylesOnboard.includes(p.id)).map(p => p.name);
    const preferredGender = quizGender === "male" ? "male" : "female";
    const inventorySource = stockroomItems.length > 0 ? stockroomItems : closetItems;
    const recommendationInventory = inventorySource.filter((item) => {
      return !item.gender || item.gender === preferredGender || item.gender === "unisex";
    });
    const recommendationCandidates = recommendationInventory.length > 0 ? recommendationInventory : inventorySource;

    setIsRecommending(true);
    setRecsQueue([]);
    setQueueIndex(0);
    setGeneratedVisualUrl(null);
    setVisualError(null);
    setVisualGuardrail(null);
    autoTryOnKeyRef.current = "";
    setRecommendationTraceStack([
      {
        label: "Survey profile",
        detail: `${activePreferences.length} selected styles and ${likedQuizOutfits.length} liked survey images queued for Gemini.`,
        status: "active",
      },
    ]);

    try {
      const profile = await api.buildPreferenceProfile({
        preferences: activePreferences,
        likedQuizOutfits: STYLE_QUIZ_OUTFITS.filter((outfit) => likedQuizOutfits.includes(outfit.id)),
        selfieDescription,
        selfieImage,
        prompt: userPrompt,
        inspirationImage,
        styleVector: userStyleVector,
        gender: quizGender,
      });
      const generatedProfile = profile.preferenceProfile || "";
      setPreferenceProfile(generatedProfile);
      upsertRecommendationTrace({
        label: "Survey profile",
        detail: `Gemini built ${policyLinesFromProfile(generatedProfile).length} policy lines from the survey and image inputs.`,
        status: "complete",
      });
      upsertRecommendationTrace({
        label: "Inventory search",
        detail: `Searching ${recommendationCandidates.length} dataset2 catalog candidates for the customer request.`,
        status: "active",
      });

      const data = await api.getRecommendations({
        preferences: activePreferences,
        closet: recommendationCandidates,
        selfieDescription: selfieDescription,
        selfieImage,
        prompt: userPrompt,
        inspirationImage: inspirationImage,
        styleVector: userStyleVector,
        preferenceProfile: generatedProfile,
        gender: quizGender === "male" ? "mens" : "womens",
      });

      if (data.recommendations && data.recommendations.length > 0) {
        setRecommendationTraceStack([
          {
            label: "Survey profile",
            detail: `Gemini built ${policyLinesFromProfile(generatedProfile).length} policy lines from the survey and image inputs.`,
            status: "complete",
          },
          ...(data.traceStack || []),
        ]);
        setRecsQueue(data.recommendations);
      } else {
        throw new Error("No clothing matching coordinates compiled.");
      }
    } catch (err: any) {
      console.error("Failed recommendation fetch:", err);
      upsertRecommendationTrace({
        label: "Recommendation",
        detail: err?.message || String(err),
        status: "error",
      });
      setRecsQueue([]);
    } finally {
      setIsRecommending(false);
    }
  };

  // Like current Rec
  const handleLikeCurrentOutfit = (outfit: OutfitRecommendation) => {
    const exists = likedOutfits.some((o) => o.outfitName === outfit.outfitName);
    if (!exists) {
      const savedObj = {
        id: `liked-${Date.now()}`,
        outfitName: outfit.outfitName,
        rationale: outfit.rationale,
        items: outfit.items.map((i) => i.name),
        onlineSourced: outfit.onlineSourced,
        tryOnAdvice: outfit.tryOnAdvice,
        likedAt: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
      };
      setLikedOutfits((prev) => [savedObj, ...prev]);
    }

    setLikedRecFeedback(true);
    setTimeout(() => {
      setLikedRecFeedback(false);
      // Advance or finish queue
      handleSelectRecommendation(queueIndex + 1);
    }, 1800);
  };

  const handleSelectRecommendation = (index: number) => {
    setQueueIndex(index);
    setGeneratedVisualUrl(null);
    setVisualError(null);
    setVisualGuardrail(null);
    setLikedRecFeedback(false);
  };

  // Dislike / Skip Outfit
  const handleDislikeCurrentOutfit = () => {
    handleSelectRecommendation(queueIndex + 1);
  };

  // Generate synthetic Try On rendering
  const handleGenerateSyntheticRender = useCallback(async (outfit: OutfitRecommendation) => {
    setIsGeneratingVisual(true);
    setGeneratedVisualUrl(null);
    setVisualError(null);
    setVisualGuardrail(null);

    const itemsStr = outfit.items.map(i => i.name).join(", ");
	    const resolvedItems = outfit.items.map((item) => {
	      const fullItemObj = closetItems.find(c => c.id === item.id || c.name === item.name);
	      const imageUrl = item.imageUrl || fullItemObj?.imageUrl;
	      const buyUrl = item.buyUrl || item.productLink || fullItemObj?.productLink;
      return {
        id: item.id,
        name: item.name,
        category: item.category,
        color: item.color || fullItemObj?.color,
        brand: item.brand || fullItemObj?.brand,
        imageUrl,
        buyUrl,
        productLink: buyUrl,
      };
    });
    const itemImages = Array.from(new Set(resolvedItems.map((item) => item.imageUrl).filter(Boolean) as string[]));
    upsertRecommendationTrace({
      label: "Try-on generation",
      detail: `Sending ${itemImages.length} recommended garment images with the shopper portrait.`,
      status: "active",
    });

    try {
      const data = await api.generateTryOnImage({
        outfitName: outfit.outfitName,
        prompt: userPrompt || "Cozy look",
        itemsStr,
        items: resolvedItems,
        itemImages,
        selfieBase64: selfieImage,
      });
      setVisualGuardrail(data.guardrail || null);
      if (data.imageUrl) {
        setGeneratedVisualUrl(data.imageUrl);
        if (data.error) {
          setVisualError(`Warning: ${data.error}`);
        }
      } else if (data.simulatedUrl) {
        setGeneratedVisualUrl(data.simulatedUrl);
        if (data.error) {
          setVisualError(`Simulation active: ${data.error}`);
        }
      } else if (data.advice) {
        if (selfieImage) {
          setGeneratedVisualUrl(selfieImage);
        }
        setVisualError(data.advice);
      } else {
        throw new Error("No image URL returned by the visualization service");
      }
      upsertRecommendationTrace({
        label: "Try-on generation",
        detail:
          data.source === "gemini_image"
            ? `Gemini returned a generated try-on image using ${data.garmentReferenceCount ?? itemImages.length} garment references.`
            : `Gemini returned try-on advice using ${data.garmentReferenceCount ?? itemImages.length} garment references, without a generated image.`,
        status: "complete",
      });
      if (data.guardrail) {
        upsertRecommendationTrace({
          label: "Image guardrail",
          detail:
            data.guardrail.status === "checked"
              ? `Guardrail ${data.guardrail.pass ? "passed" : "flagged review"}${typeof data.guardrail.faithfulness_score === "number" ? ` at ${data.guardrail.faithfulness_score.toFixed(2)}` : ""}.`
              : `${data.guardrail.status || "skipped"}: ${(data.guardrail.issues || []).join("; ")}`,
          status: data.guardrail.status === "error" ? "error" : "complete",
        });
      }
    } catch (err: any) {
      console.error("Failed to generate image on backend:", err);
      setVisualError(`Generation failed: ${err.message || err}.`);
      upsertRecommendationTrace({
        label: "Try-on generation",
        detail: err?.message || String(err),
        status: "error",
      });
    } finally {
      setIsGeneratingVisual(false);
    }
  }, [closetItems, selfieImage, upsertRecommendationTrace, userPrompt]);

  useEffect(() => {
    if (isRecommending || recsQueue.length === 0 || queueIndex >= recsQueue.length) return;
    const outfit = recsQueue[queueIndex];
    const tryOnKey = `${queueIndex}:${outfit.outfitName}`;
    if (autoTryOnKeyRef.current === tryOnKey) return;
    autoTryOnKeyRef.current = tryOnKey;
    handleGenerateSyntheticRender(outfit);
  }, [handleGenerateSyntheticRender, isRecommending, queueIndex, recsQueue]);

  // Remove closet item
  const removeClosetItem = (id: string) => {
    setClosetItems((prev) => prev.filter((item) => item.id !== id));
  };

  // Remove liked outfit
  const removeLikedOutfit = (id: string) => {
    setLikedOutfits((prev) => prev.filter((o) => o.id !== id));
  };

  // Mock preset library to let users click & load instantly
  const clothingPresets = [
    {
      name: "Calvin Klein Fitted Silk Blazer",
      category: "Outerwear" as GarmentCategory,
      color: "Rich Brown Walnut",
      pattern: "Smooth satin silk blend",
      vibe: "90s minimalism, sharp executive structure, corporate chic",
      image: "https://images.unsplash.com/photo-1544022613-e87ca75a784a?auto=format&fit=crop&q=80&w=400",
      brand: "Calvin Klein",
      gender: "female" as const
    },
    {
      name: "Levi's Wide-Leg Pleated Denim",
      category: "Bottoms" as GarmentCategory,
      color: "Deep Indigo Wash",
      pattern: "Rigid unwashed cotton twill",
      vibe: "High waist wide leg, elegant maritime posture",
      image: "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&q=80&w=400",
      brand: "Levi's",
      gender: "female" as const
    },
    {
      name: "Charter Club Ribbed Camel Pullover",
      category: "Tops" as GarmentCategory,
      color: "Oatmeal Beige",
      pattern: "Ribbed cashmere knit weave",
      vibe: "Soft classic cozy base layer, ultra luxury feel",
      image: "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&q=80&w=400",
      brand: "Charter Club",
      gender: "female" as const
    },
    {
      name: "Tommy Hilfiger Heritage Trainers",
      category: "Shoes" as GarmentCategory,
      color: "Pristine White",
      pattern: "Smooth leather with gold emblem accent",
      vibe: "Sporty collegiate streetwear bounce, durable support",
      image: "https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&q=80&w=400",
      brand: "Tommy Hilfiger",
      gender: "male" as const
    }
  ];

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-200 font-sans selection:bg-amber-100 selection:text-neutral-200 overflow-x-hidden">
      
      {/* ONBOARDING OVERLAY */}
      <AnimatePresence>
        {!hasCompletedOnboarding && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-neutral-950 overflow-y-auto flex flex-col items-center justify-start p-6 md:p-12 font-sans selection:bg-amber-100 selection:text-neutral-950"
          >
            <div className="max-w-5xl w-full my-auto text-center">
              
              {/* STEP PROGRESS CRUMB */}
              <div className="flex justify-center items-center space-x-3 mb-8">
                <button 
                  onClick={() => setOnboardingStep(1)}
                  className={`px-3 py-1.5 rounded-full text-xs font-mono border transition-all ${
                    onboardingStep === 1 
                      ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-550/20 font-semibold" 
                      : "bg-neutral-900 text-neutral-400 border-neutral-800 hover:text-white"
                  }`}
                >
                  STEP 01: STYLE PREFERENCE
                </button>
                <div className="h-px w-8 bg-neutral-800" />
                <button 
                  onClick={() => setOnboardingStep(2)}
                  className={`px-3 py-1.5 rounded-full text-xs font-mono border transition-all ${
                    onboardingStep === 2 
                      ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-550/20 font-semibold" 
                      : "bg-neutral-900 text-neutral-400 border-neutral-800 hover:text-white"
                  }`}
                >
                  STEP 02: TRY-ON PORTRAIT
                </button>
                <div className="h-px w-8 bg-neutral-800" />
                <button 
                  onClick={() => setOnboardingStep(3)}
                  className={`px-3 py-1.5 rounded-full text-xs font-mono border transition-all ${
                    onboardingStep === 3 
                      ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-550/20 font-semibold" 
                      : "bg-neutral-900 text-neutral-400 border-neutral-800 hover:text-white"
                  }`}
                >
                  STEP 03: FIT & MORPH PLAN
                </button>
              </div>

              {onboardingStep === 1 && (
                /* STEP 1: INTERACTIVE PHOTO STYLE QUIZ */
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-6"
                >
                  <div className="inline-flex space-x-2 items-center bg-white border border-neutral-800 text-neutral-500 px-3 py-1.5 rounded-full text-xs font-mono mb-2 tracking-wider shadow-sm select-none">
                    <Cpu className="w-3.5 h-3.5 text-indigo-600 animate-pulse" />
                    <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 bg-clip-text text-transparent font-semibold">CODENAME: STYLING IDENTITY AGENT</span>
                  </div>
                  
                  <h1 className="font-display font-bold text-3xl md:text-5xl text-neutral-100 tracking-tight">
                    Calibrate Your <span className="bg-gradient-to-r from-blue-600 via-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent italic font-extrabold uppercase">Style DNA</span>
                  </h1>
                  <p className="text-neutral-400 max-w-2xl mx-auto text-xs md:text-sm font-light leading-relaxed">
                    Show us what you love. Tap the outfit concepts below that resonate with your personal vibe. We'll instantly map them to an 8-dimensional style embedding vector to pre-train your digitized wardrobe.
                  </p>

                  <div className="max-w-4xl mx-auto bg-neutral-900/45 border border-neutral-850 p-6 rounded-2xl space-y-4 text-left">
                    <div className="flex flex-col sm:flex-row items-center justify-between pb-2 border-b border-neutral-800 gap-2">
                      <span className="text-xs font-mono text-neutral-300 uppercase tracking-wider font-semibold">01. TAP INSPIRATIONAL STYLE ARCHETYPES</span>
                      
                      {/* HIGH-CONTRAST DYNAMIC GENDER SELECTOR */}
                      <div className="flex bg-neutral-950 p-0.5 border border-neutral-800 rounded-full">
                        <button
                          type="button"
                          onClick={() => {
                            setQuizGender("female");
                            localStorage.setItem("user_quiz_gender", "female");
                            setSelfieImage("https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=600");
                            setSelfieDescription("Warm bronze skin tones, feminine form, suited for fluid and tailored layering combinations.");
                          }}
                          className={`px-3 py-1 text-[10px] font-mono uppercase rounded-full transition-all ${
                            quizGender === "female"
                              ? "bg-amber-100 text-neutral-900 font-semibold"
                              : "text-neutral-500 hover:text-white"
                          }`}
                        >
                          Female
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setQuizGender("male");
                            localStorage.setItem("user_quiz_gender", "male");
                            setSelfieImage("https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=600");
                            setSelfieDescription("Subtle natural undertone, masculine frame, athletic structure, suited for structured clean casual fits.");
                          }}
                          className={`px-3 py-1 text-[10px] font-mono uppercase rounded-full transition-all ${
                            quizGender === "male"
                              ? "bg-amber-100 text-neutral-900 font-semibold"
                              : "text-neutral-500 hover:text-white"
                          }`}
                        >
                          Male
                        </button>
                      </div>
                    </div>

                    {/* 12-15 RANDOM OUTFITS GRID (FILTERED BY GENDER) */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 max-h-[420px] overflow-y-auto pr-2 custom-scrollbar text-left">
                      {STYLE_QUIZ_OUTFITS.filter(o => o.gender === quizGender).map((outfit) => {
                        const isLiked = likedQuizOutfits.includes(outfit.id);
                        return (
                          <div
                            key={outfit.id}
                            onClick={() => handleToggleQuizOutfit(outfit.id)}
                            className={`group relative cursor-pointer overflow-hidden rounded-xl border transition-all duration-300 ${
                              isLiked 
                                ? "border-amber-400 bg-neutral-900 ring-2 ring-amber-400/25 scale-[0.98]" 
                                : "border-neutral-800 bg-neutral-950 hover:border-neutral-700 hover:scale-[1.01]"
                            }`}
                          >
                            <div className="aspect-[3/4] overflow-hidden relative grayscale group-hover:grayscale-0 transition-all duration-300">
                              <img 
                                src={outfit.imageUrl} 
                                alt={outfit.aesthetic} 
                                className="w-full h-full object-cover group-hover:scale-105 transition-all duration-500"
                                referrerPolicy="no-referrer"
                              />
                              {/* Overlay tag */}
                              <div className="absolute top-2 left-2 bg-neutral-950/80 backdrop-blur-md text-[8px] font-mono text-neutral-200 px-1.5 py-0.5 rounded tracking-wider uppercase">
                                {outfit.aesthetic}
                              </div>
                              {/* Checkmark indicator */}
                              <div className={`absolute top-2 right-2 rounded-full p-1 transition-all ${
                                isLiked ? "bg-amber-300 text-neutral-900 scale-100" : "bg-neutral-900/40 text-transparent scale-0"
                              }`}>
                                <Check className="w-3.5 h-3.5 stroke-[3px]" />
                              </div>
                            </div>
                            
                            <div className="p-2 text-[9px] bg-neutral-900/95 leading-normal border-t border-neutral-850 h-10 flex items-center">
                              <p className="text-neutral-300 line-clamp-2 italic font-light font-sans">{outfit.description}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Actions buttons */}
                  <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4 justify-center pt-4 border-t border-neutral-900 mt-6 max-w-4xl mx-auto">
                    <button
                      type="button"
                      onClick={() => {
                        // Completely skip onboarding and jump straight into the application
                        if (selectedStylesOnboard.length === 0) {
                          setSelectedStylesOnboard(DEFAULT_SELECTED_STYLE_IDS);
                        }
                        handleCompleteOnboarding();
                      }}
                      className="px-6 py-2.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded-lg text-sm hover:bg-neutral-800 transition-all font-mono"
                    >
                      SKIP ALL ONBOARDING (USE DEFAULT PLAN)
                    </button>
                    <button
                      type="button"
                      onClick={() => setOnboardingStep(2)}
                      className="px-8 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-lg text-sm flex items-center justify-center space-x-2 transition-all shadow-lg text-center"
                    >
                      <span>Continue to Try-On Portrait</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              )}

              {onboardingStep === 2 && (
                /* STEP 2: TRY-ON PORTRAIT */
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-6"
                >
                  <div className="inline-flex space-x-2 items-center bg-white border border-neutral-800 text-neutral-500 px-3 py-1.5 rounded-full text-xs font-mono mb-2 tracking-wider shadow-sm select-none">
                    <ImageIcon className="w-3.5 h-3.5 text-indigo-600 animate-pulse" />
                    <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 bg-clip-text text-transparent font-semibold">CODENAME: COMPUTER VISION PORTRAIT AGENT</span>
                  </div>
                  
                  <h1 className="font-display font-bold text-3xl md:text-5xl text-neutral-100 tracking-tight">
                    Step 02: Try-On <span className="bg-gradient-to-r from-blue-600 via-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent italic font-extrabold uppercase">Portrait Model</span>
                  </h1>
                  <p className="text-neutral-400 max-w-2xl mx-auto text-xs md:text-sm font-light leading-relaxed">
                    Upload your personal portrait photo below to map physical color tone and frame templates under computer-vision guidance, or skip to use default styles.
                  </p>

                  <div className="max-w-md mx-auto bg-neutral-900 border border-neutral-850 p-6 rounded-2xl text-left space-y-4 shadow-xl">
                    <div className="pb-2 border-b border-neutral-800">
                      <span className="text-xs font-mono text-neutral-300 uppercase tracking-wider font-semibold">TRY-ON PORTRAIT (CAN SKIP)</span>
                    </div>

                    {/* Try-on model image container */}
                    <div className="relative aspect-[3/4] rounded-xl overflow-hidden bg-neutral-950 border border-neutral-800 group max-w-[280px] mx-auto shadow-sm">
                      {selfieImage ? (
                        <>
                          <img 
                            src={selfieImage} 
                            alt="Try-On Portrait Model" 
                            className="w-full h-full object-cover grayscale opacity-90 group-hover:grayscale-0 transition-all duration-500"
                            referrerPolicy="no-referrer"
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-neutral-950/85 via-neutral-950/10 to-transparent" />
                          <div className="absolute top-2.5 right-2.5 flex space-x-1">
                            <button
                              type="button"
                              onClick={() => setSelfieImage(null)}
                              className="bg-neutral-950/80 hover:bg-rose-600 text-white rounded-full p-1.5 transition-all"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          <span className="absolute bottom-2.5 left-2.5 text-[9px] font-mono text-emerald-400 bg-neutral-950/85 px-2 py-0.5 rounded border border-emerald-950/40">
                            ✓ Registered
                          </span>
                        </>
                      ) : (
                        <label className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center cursor-pointer hover:bg-neutral-900/30 transition-all border border-dashed border-neutral-800 rounded-xl">
                          <Upload className="w-8 h-8 text-neutral-500 mb-2" />
                          <span className="text-xs text-neutral-300 font-medium">Upload model/selfie image</span>
                          <span className="text-[9px] text-neutral-500 mt-1 max-w-[180px] leading-normal font-light">
                            Optional portrait upload. Grab from system or camera.
                          </span>
                          <input 
                            type="file" 
                            accept="image/*" 
                            className="hidden" 
                            onChange={(e) => handleFileChange(e, "selfie")}
                          />
                        </label>
                      )}
                    </div>

                    {/* Quick descriptor traits of the body/skin */}
                    <div className="space-y-1">
                      <label className="block text-[8px] font-mono text-neutral-400 uppercase tracking-widest">
                        Body & Skin Tone Traits
                      </label>
                      <textarea
                        value={selfieDescription}
                        onChange={(e) => {
                          setSelfieDescription(e.target.value);
                          localStorage.setItem("user_selfie_desc", e.target.value);
                        }}
                        placeholder="Feminine, slim/athletic, warm olive skin temperature..."
                        className="w-full bg-neutral-950 border border-neutral-800 p-2 text-[10px] text-neutral-300 rounded-lg focus:outline-none focus:border-amber-400/40 font-mono"
                        rows={2}
                      />
                    </div>
                  </div>

                  {/* Actions buttons */}
                  <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4 justify-center pt-4 border-t border-neutral-900 mt-6 max-w-md mx-auto">
                    <button
                      type="button"
                      onClick={() => setOnboardingStep(1)}
                      className="px-6 py-2.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded-lg text-sm hover:bg-neutral-800 transition-all font-mono"
                    >
                      ← STYLE PREFERENCE
                    </button>
                    <button
                      type="button"
                      onClick={() => setOnboardingStep(3)}
                      className="px-8 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-lg text-sm flex items-center justify-center space-x-2 transition-all shadow-lg text-center font-sans"
                    >
                      <span>Continue to Fit &amp; Morph Plan</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              )}

              {onboardingStep === 3 && (
                /* STEP 3: CATEGORY FINE-TUNING & SELFIE CHECKS */
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-6"
                >
                  <h1 className="font-display font-bold text-3xl md:text-4xl text-neutral-100 tracking-tight">
                    Fine-Tune Your <span className="text-amber-300 italic font-semibold">Morph</span> Framework
                  </h1>
                  <p className="text-neutral-400 max-w-xl mx-auto text-xs font-light">
                    Establish styling boundaries and help our computer vision model match clothes to your natural colors and build pointers.
                  </p>

                  {/* Core Styles Pref choices grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mb-6 text-left">
                    {STYLE_PREF_CHOICES.map((pref) => {
                      const isSelected = selectedStylesOnboard.includes(pref.id);
                      return (
                        <div
                          key={pref.id}
                          onClick={() => {
                            setSelectedStylesOnboard((prev) =>
                              prev.includes(pref.id)
                                ? prev.filter((id) => id !== pref.id)
                                : [...prev, pref.id]
                            );
                          }}
                          className={`group relative cursor-pointer overflow-hidden rounded-xl border transition-all duration-300 ${
                            isSelected 
                              ? "border-amber-300 bg-neutral-900 ring-2 ring-amber-400/25" 
                              : "border-neutral-800 bg-neutral-900/40 hover:border-neutral-700 hover:bg-neutral-900/70"
                          }`}
                        >
                          <div className="p-3">
                            <div className="flex justify-between items-center mb-1">
                              <h3 className="font-display font-medium text-white text-sm tracking-tight">
                                {pref.name}
                              </h3>
                              {isSelected ? (
                                <div className="bg-amber-100 text-neutral-900 rounded-full p-0.5">
                                  <Check className="w-2.5 h-2.5 stroke-[3px]" />
                                </div>
                              ) : null}
                            </div>
                            <p className="text-[10px] text-neutral-400 font-light line-clamp-2 leading-relaxed">
                              {pref.description}
                            </p>
                            <div className="mt-2 text-[8px] font-mono text-neutral-500 uppercase tracking-wider">
                              VIBE: {pref.vibeText}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Textarea description fit */}
                  <div className="max-w-xl mx-auto mb-4 text-left bg-neutral-900/60 border border-neutral-800 rounded-xl p-4">
                    <label className="block text-[10px] font-mono uppercase tracking-wider text-neutral-400 mb-2">
                      Body Framework & Palette Constraints (Extracts color temperature)
                    </label>
                    <textarea
                      value={selfieTraitsInput}
                      onChange={(e) => setSelfieTraitsInput(e.target.value)}
                      className="w-full bg-neutral-950 border border-neutral-800 rounded-lg p-3 text-xs text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-amber-400/50 transition-all font-mono"
                      rows={3}
                      placeholder="Tell the AI Agent any specific clothing fit notes (e.g. warm skin tones, slim athletic, etc.)..."
                    />
                  </div>

                  {/* Optional Image Upload for Finding Similar Clothes */}
                  <div className="max-w-xl mx-auto mb-6 text-left bg-neutral-900/60 border border-neutral-800 rounded-xl p-4">
                    <label className="block text-[10px] font-mono uppercase tracking-wider text-neutral-400 mb-2">
                       Optional Outfit Photo (To match similar clothes)
                    </label>
                    
                    {inspirationImage ? (
                      <div className="relative aspect-video rounded-lg overflow-hidden border border-amber-300/40 bg-neutral-950">
                        <img 
                          src={inspirationImage} 
                          alt="Outfit Inspiration match target" 
                          className="w-full h-full object-cover" 
                          referrerPolicy="no-referrer"
                        />
                        <button
                          type="button"
                          onClick={() => setInspirationImage(null)}
                          className="absolute top-2 right-2 bg-neutral-950/80 hover:bg-rose-500 text-white rounded-full p-1.5 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center border-2 border-dashed border-neutral-800 hover:border-amber-400/30 rounded-xl p-4 cursor-pointer bg-neutral-950 transition-all text-center">
                        <Upload className="w-5 h-5 text-neutral-500 mb-1.5" />
                        <span className="text-xs text-neutral-300 font-medium">Click to upload reference outfit photo (Optional)</span>
                        <span className="text-[10px] text-neutral-500 mt-1 max-w-sm leading-normal">
                          We will evaluate visual colors and textures in this image and search the Amazon store catalog inventory for similar elements.
                        </span>
                        <input 
                          type="file" 
                          accept="image/*" 
                          className="hidden" 
                          onChange={(e) => handleFileChange(e, "inspiration")}
                        />
                      </label>
                    )}
                  </div>

                  {/* Action row */}
                  <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4 justify-center">
                    <button
                      onClick={() => setOnboardingStep(1)}
                      className="px-6 py-2.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded-lg text-sm hover:bg-neutral-800 transition-all font-mono"
                    >
                      ← PREVIOUS STEP
                    </button>
                    <button
                      onClick={() => {
                        // Skip Step 2 fine-tuning, directly complete using Step 1 choices
                        if (selectedStylesOnboard.length === 0) {
                          setSelectedStylesOnboard(DEFAULT_SELECTED_STYLE_IDS);
                        }
                        handleCompleteOnboarding();
                      }}
                      className="px-6 py-2.5 bg-neutral-950 border border-neutral-850 text-neutral-400 hover:text-white rounded-lg text-sm hover:bg-neutral-900 transition-all font-mono"
                    >
                      SKIP &amp; USE STEP 01 DEFAULTS
                    </button>
                    <button
                      onClick={() => {
                        // Apply reasonable defaults if non-selected
                        if (selectedStylesOnboard.length === 0) {
                          setSelectedStylesOnboard(DEFAULT_SELECTED_STYLE_IDS);
                        }
                        handleCompleteOnboarding();
                      }}
                      className="px-10 py-2.5 bg-amber-200 hover:bg-amber-300 text-neutral-950 font-semibold rounded-lg text-sm flex items-center justify-center space-x-2 transition-all shadow-md active:scale-95 duration-200"
                    >
                      <span>Build Customer Fitting Profile</span>
                      <Check className="w-4 h-4 ml-1" />
                    </button>
                  </div>
                </motion.div>
              )}

            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* HEADER BAR */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-neutral-800 py-4 px-6 md:px-12 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                 <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab("discover")}>
            <div className="bg-gradient-to-tr from-blue-600 via-indigo-500 via-purple-500 to-pink-500 text-white p-2.5 rounded-xl shadow-md">
              <Shirt className="w-5 h-5 stroke-[2.2px]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-display font-semibold text-lg tracking-tight bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 bg-clip-text text-transparent">Personal Fitting Advisor</span>
              </div>
              <p className="text-[10px] text-neutral-600 font-mono tracking-wide">AI STORE FITTING SUITE</p>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="flex space-x-1 bg-neutral-850 border border-neutral-800 rounded-full p-1 text-xs md:text-sm">
            <button
              id="tab-discover"
              onClick={() => setActiveTab("discover")}
              className={`px-4 py-1.5 rounded-full transition-all duration-300 flex items-center space-x-1.5 ${
                activeTab === "discover" 
                  ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white font-medium shadow-md shadow-indigo-100/45" 
                  : "text-neutral-500 hover:text-neutral-800"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Personal Stylist Advisor</span>
            </button>
            <button
              id="tab-closet"
              onClick={() => setActiveTab("closet")}
              className={`px-4 py-1.5 rounded-full transition-all duration-300 flex items-center space-x-1.5 ${
                activeTab === "closet" 
                  ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white font-medium shadow-md shadow-indigo-100/45" 
                  : "text-neutral-500 hover:text-neutral-800"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Store Inventory ({closetItems.length}{catalogTotal > closetItems.length ? ` / ${catalogTotal}` : ''})</span>
            </button>
            <button
              id="tab-liked"
              onClick={() => setActiveTab("liked")}
              className={`px-4 py-1.5 rounded-full transition-all duration-300 flex items-center space-x-1.5 ${
                activeTab === "liked" 
                  ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white font-medium shadow-md shadow-indigo-100/45" 
                  : "text-neutral-500 hover:text-neutral-800"
              }`}
            >
              <Heart className="w-3.5 h-3.5" />
              <span>Favorites ({likedOutfits.length})</span>
            </button>
            <button
              id="tab-designdoc"
              onClick={() => setActiveTab("designdoc")}
              className={`px-4 py-1.5 rounded-full transition-all duration-300 flex items-center space-x-1.5 ${
                activeTab === "designdoc" 
                  ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white font-medium shadow-md shadow-indigo-100/45" 
                  : "text-neutral-500 hover:text-neutral-800"
              }`}
            >
              <FileCheck2 className="w-3.5 h-3.5" />
              <span>Design Document</span>
            </button>
          </nav>

          <div className="flex space-x-2 items-center text-xs">
            <button 
              onClick={resetOnboarding}
              className="text-neutral-500 hover:text-indigo-600 hover:border-indigo-300 font-mono transition-all border border-neutral-800 bg-neutral-900/10 px-3 py-1.5 rounded-lg text-[10px] uppercase cursor-pointer"
            >
              RESET PROFILE
            </button>
            {backendConnected !== null && (
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-[9px] font-mono border ${
                backendConnected 
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                  : "bg-amber-500/10 text-amber-400 border-amber-500/20"
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${backendConnected ? "bg-emerald-400" : "bg-amber-400"}`} />
                {backendConnected ? "BACKEND ONLINE" : "LOCAL MODE"}
              </span>
            )}
          </div>

        </div>
      </header>

      {/* BODY CONTENT CONTAINER */}
      <main className="max-w-7xl mx-auto px-6 md:px-12 py-8">
               {/* DISCOVER & TRY-ON TAB */}
        {activeTab === "discover" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            
            {/* Survey/profile inputs are kept out of the main clerk flow. */}
            <div className="hidden">
              
              {/* Selfie Frame & Demographics */}
              <div className="border border-neutral-800/85 bg-neutral-900/30 rounded-2xl p-5 overflow-hidden">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4 text-amber-200" />
                    <h2 className="font-display font-medium text-sm text-white uppercase tracking-wider">Try-On Model Portrait & Morph Traits</h2>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-400">REGISTERED</span>
                </div>

                <div className="relative aspect-3/4 rounded-xl overflow-hidden bg-neutral-950 border border-neutral-850 mb-4 group">
                  {selfieImage ? (
                    <>
                      <img 
                        src={selfieImage} 
                        alt="User Selfie Model" 
                        className="w-full h-full object-cover grayscale opacity-90 group-hover:grayscale-0 transition-all duration-500"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-neutral-950/80 to-transparent" />
                    </>
                  ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
                      <ImageIcon className="w-8 h-8 text-neutral-500 mb-2" />
                      <span className="text-xs text-neutral-400 hover:underline cursor-pointer">
                        Upload custom model selfie
                      </span>
                    </div>
                  )}

                  <div className="absolute bottom-3 left-3 right-3 flex justify-between items-center">
                    <label className="text-[11px] bg-neutral-900 hover:bg-neutral-850 text-neutral-200 font-mono border border-neutral-800 px-3 py-1.5 rounded-lg cursor-pointer transition-colors">
                      <Upload className="w-3 h-3 inline-block mr-1.5 align-middle" />
                      <span>Change Model Portrait</span>
                      <input 
                        type="file" 
                        accept="image/*" 
                        className="hidden" 
                        onChange={(e) => handleFileChange(e, "selfie")}
                      />
                    </label>
                    <button 
                      onClick={() => setSelfieImage(quizGender === "male" 
                        ? "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=600"
                        : "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=600"
                      )}
                      className="text-[10px] text-amber-200/80 bg-neutral-950/60 hover:bg-neutral-950 px-2.5 py-1.5 rounded border border-neutral-800 font-mono transition"
                    >
                      RESET MODEL
                    </button>
                  </div>
                </div>

                {/* Body details descriptions */}
                <div className="space-y-2">
                  <label className="block text-[10px] uppercase font-mono tracking-wider text-neutral-400">
                    Body Morph & Undertone Traits
                  </label>
                  <textarea
                    value={selfieDescription}
                    onChange={(e) => {
                      setSelfieDescription(e.target.value);
                      localStorage.setItem("user_selfie_desc", e.target.value);
                    }}
                    className="w-full bg-neutral-950/80 border border-neutral-850 rounded-lg p-3 text-xs text-neutral-205 placeholder-neutral-605 focus:outline-none focus:border-amber-400/30 transition-all font-mono"
                    rows={2}
                    placeholder="Enter physical traits like heights, skin tone..."
                  />
                  <p className="text-[9px] text-neutral-500 italic">
                    AI Agent aligns fabric colors and cut parameters based on these pointers to suggest fitting silhouettes.
                  </p>
                </div>

              </div>

              {/* RE-TAKE QUIZ BOX (REPLACES ACTIVE STYLE DNA DIAGNOSTICS) */}
              <div className="border border-amber-500/15 bg-neutral-900/40 rounded-2xl p-5 shadow-lg space-y-3.5 text-left">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-amber-300 animate-pulse" />
                    <h2 className="font-display font-semibold text-xs text-amber-200 uppercase tracking-widest">Style DNA Profile</h2>
                  </div>
                </div>
                <p className="text-[11px] text-neutral-300 font-light leading-normal">
                  Your style preference vector is calibrated and ready. Retaking the quiz will reset your calibration parameters.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setHasCompletedOnboarding(false);
                    setOnboardingStep(1);
                  }}
                  className="w-full py-3 px-4 bg-gradient-to-r from-amber-400 via-amber-500 to-yellow-500 hover:from-amber-300 hover:to-yellow-400 text-neutral-950 font-mono text-xs uppercase rounded-xl transition-all duration-300 flex items-center justify-center space-x-2 shadow-lg shadow-amber-500/20 font-bold cursor-pointer hover:scale-[1.01] active:scale-[0.98]"
                >
                  <RotateCcw className="w-3.5 h-3.5 stroke-[2.5] animate-spin-slow" />
                  <span>RE-TAKE STYLE QUIZ</span>
                </button>
              </div>

            </div>

            {/* Customer request */}
            <div className="lg:col-span-4 space-y-6">
              
              {/* Dynamic prompts and vibes builder */}
              <div className="border border-neutral-800 bg-neutral-900/40 rounded-2xl p-5 shadow-lg">
                <div className="flex items-center space-x-2 mb-4">
                  <Sparkles className="w-4 h-4 text-amber-200" />
	                  <h2 className="font-display font-medium text-sm text-white uppercase tracking-widest">Customer Request</h2>
                </div>

                {/* Prompt textarea */}
                <div className="space-y-3">
                  <div>
                    <label className="block text-[10px] uppercase font-mono tracking-wider text-neutral-400 mb-1.5">
	                      What does the customer need?
                    </label>
                    <textarea
                      value={userPrompt}
                      onChange={(e) => setUserPrompt(e.target.value)}
	                      placeholder="e.g. dinner after work, rainy commute outfit, conference look..."
                      className="w-full h-24 bg-neutral-950 border border-neutral-850 rounded-xl p-3 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-amber-500/40 focus:ring-1 focus:ring-amber-400/20 transition-all font-sans leading-normal"
                    />
                  </div>

                  {/* Suggest shortcut prompt blocks */}
                  <div>
	                    <span className="block text-[9px] font-mono text-neutral-500 uppercase mb-1">Quick Presets</span>
                    <div className="flex flex-wrap gap-1.5">
                      {[
	                        "Rainy commute",
	                        "Dinner after work",
	                        "Conference look",
	                        "Weekend outdoors"
                      ].map((presetPrompt) => (
                        <button
                          key={presetPrompt}
                          onClick={() => setUserPrompt(presetPrompt)}
                          className="text-[10px] text-neutral-400 hover:text-white bg-neutral-950 border border-neutral-850 hover:bg-neutral-900 px-2 py-1 rounded transition"
                        >
                          {presetPrompt}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Optional similar garments reference image uploader */}
                  <div className="border-t border-neutral-850 pt-3">
                    <label className="block text-[10px] uppercase font-mono tracking-wider text-neutral-450 mb-2">
	                      Optional Reference Image
                    </label>
                    
                    {inspirationImage ? (
                      <div className="relative aspect-video rounded-lg overflow-hidden border border-amber-300/40">
                        <img 
                          src={inspirationImage} 
                          alt="Inspiration reference for similar clothes" 
                          className="w-full h-full object-cover" 
                          referrerPolicy="no-referrer"
                        />
                        <button
                          onClick={() => setInspirationImage(null)}
                          className="absolute top-2 right-2 bg-neutral-950/80 hover:bg-rose-500 text-white rounded-full p-1.5 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <label className="flex flex-col items-center justify-center border-2 border-dashed border-neutral-800 hover:border-amber-305/30 rounded-xl p-3 cursor-pointer bg-neutral-950 transition-colors text-center">
                        <Upload className="w-4 h-4 text-neutral-500 mb-1" />
	                        <span className="text-[11px] text-neutral-300 font-medium">Upload reference image</span>
                        <input 
                          type="file" 
                          accept="image/*" 
                          className="hidden" 
                          onChange={(e) => handleFileChange(e, "inspiration")}
                        />
                      </label>
                    )}
                  </div>

                  {/* Submit request button */}
                  <button
                    onClick={requestStylingRecommendations}
                    disabled={isRecommending}
                    className="w-full mt-2 py-3 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl text-sm flex items-center justify-center space-x-2 transition-all shadow-lg text-center font-display disabled:opacity-50 hover:shadow-indigo-200/50 hover:shadow-xl active:scale-[0.99]"
                  >
                    <span>
	                      {isRecommending ? "Working..." : "Get Recommendations"}
                    </span>
                    <Sparkles className="w-4 h-4 text-white animate-pulse" />
                  </button>
                </div>

              </div>

            </div>

            {/* Recommendation output */}
            <div className="lg:col-span-8 flex flex-col space-y-6">
              
              {/* If no query has been triggered yet */}
              {recsQueue.length === 0 && !isRecommending && (
                <div className="border border-neutral-850 bg-neutral-900/10 rounded-3xl p-12 text-center flex flex-col items-center justify-center min-h-[500px]">
                  <div className="relative mb-6">
                    <div className="absolute inset-0 bg-amber-400 rounded-full blur-xl opacity-10 animate-pulse" />
                    <div className="relative bg-neutral-900 border border-neutral-800 p-6 rounded-full">
                      <Cpu className="w-12 h-12 text-amber-200" />
                    </div>
                  </div>
                  <h3 className="font-display font-light text-2xl text-white mb-3">AI Stylist Workbench</h3>
	                  <p className="text-neutral-400 max-w-lg mx-auto text-sm leading-relaxed mb-6">
	                    Macy's store catalog features <span className="text-amber-200 font-medium tracking-tight">{closetItems.length}</span> active available items. Configure search queries or inspiration parameters below, and our AI fitting suite will select specific store items to compose exactly three custom outfits.
	                  </p>
                    {recommendationTraceStack.length > 0 && (
                      <div className="w-full max-w-lg mb-6 text-left">
                        <TraceStackPanel steps={recommendationTraceStack} />
                      </div>
                    )}
	                  
	                  <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
                    <button
                      onClick={() => {
                        setUserPrompt("Weekend Date, Retro Romantic & Vintage Vibes");
                        setTimeout(() => {
                          requestStylingRecommendations();
                        }, 100);
                      }}
                      className="px-6 py-2.5 bg-neutral-900 border border-neutral-800 text-neutral-300 hover:border-amber-300/30 text-xs rounded-xl transition"
                    >
                      Try One-Click Demo: Date Fit
                    </button>
                    <button
                      onClick={() => {
                        setUserPrompt("Technology Conference Keynote, Smart Commute");
                        setTimeout(() => {
                          requestStylingRecommendations();
                        }, 100);
                      }}
                      className="px-6 py-2.5 bg-neutral-900 border border-neutral-800 text-neutral-300 hover:border-amber-300/30 text-xs rounded-xl transition"
                    >
                      Try One-Click Demo: Smart Commute
                    </button>
                  </div>
                </div>
              )}

              {/* Loading progress screen */}
              {isRecommending && (
                <div className="border border-neutral-850 bg-neutral-900/15 rounded-3xl p-6 min-h-[500px] flex flex-col justify-center">
                  <TraceStackPanel steps={recommendationTraceStack} />
                </div>
              )}

              {/* Dynamic Recs queue displays */}
              {recsQueue.length > 0 && !isRecommending && (
                <div className="space-y-4">
                  <PreferencePolicyPanel profile={preferenceProfile} />
                  <TraceStackPanel steps={recommendationTraceStack} />
                  
                  {/* Queue progress and prompts overview header */}
	                  <div className="flex items-center justify-between mb-4 px-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-mono bg-neutral-900 text-amber-200 border border-neutral-800 px-2 py-0.5 rounded uppercase">
                        Outfit Proposal {queueIndex + 1} / {recsQueue.length}
                      </span>
                      {userPrompt && (
                        <span className="text-xs text-neutral-400 truncate max-w-sm font-light">
                          For: "{userPrompt}"
                        </span>
                      )}
                    </div>
	                    <div className="flex flex-wrap justify-end gap-1">
	                      {recsQueue.map((_, i) => (
	                        <button 
	                          key={i}
                            type="button"
                            onClick={() => handleSelectRecommendation(i)}
                            aria-label={`View recommendation ${i + 1}`}
	                          className={`h-7 min-w-7 rounded-md border px-2 text-[10px] font-mono transition ${
	                            i === queueIndex 
	                              ? "bg-amber-200 text-neutral-950 border-amber-200" 
	                              : i < queueIndex 
	                                ? "bg-neutral-800 text-neutral-300 border-neutral-700 hover:border-neutral-500" 
	                                : "bg-neutral-950 text-neutral-500 border-neutral-850 hover:text-neutral-200"
	                          }`}
	                        >
                            {i + 1}
	                        </button>
	                      ))}
	                    </div>
	                  </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
                      {recsQueue.map((recommendation, i) => (
                        <button
                          key={`${recommendation.outfitName}-${i}`}
                          type="button"
                          onClick={() => handleSelectRecommendation(i)}
                          className={`min-h-16 rounded-xl border p-3 text-left transition ${
                            i === queueIndex
                              ? "border-amber-200 bg-amber-200/10"
                              : "border-neutral-850 bg-neutral-950/60 hover:border-neutral-700"
                          }`}
                        >
                          <span className="block text-[10px] font-mono text-neutral-500 uppercase">Recommendation {i + 1}</span>
                          <span className="mt-1 block text-xs font-medium text-neutral-100 line-clamp-2">{recommendation.outfitName}</span>
                          <span className="mt-1 block text-[10px] text-neutral-500">{recommendation.items.length} products</span>
                        </button>
                      ))}
                    </div>

	                  {/* Recommendation Queue boundaries */}
                  {queueIndex < recsQueue.length ? (
                    <div className="space-y-6">
                      
                      {/* Interactive Recommend Card */}
                      <AnimatePresence mode="wait">
                        <motion.div
                          key={queueIndex}
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          transition={{ duration: 0.3 }}
                          className="relative border border-neutral-800 bg-neutral-900/60 rounded-3xl p-6 md:p-8 overflow-hidden shadow-2xl"
                        >
                          
                          {/* Loved visual feedback banner */}
                          <AnimatePresence>
                            {likedRecFeedback && (
                              <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.9 }}
                                className="absolute inset-0 z-20 bg-neutral-950/95 backdrop-blur flex flex-col items-center justify-center text-center p-6"
                              >
                                <div className="bg-amber-100 text-neutral-950 rounded-full p-4 mb-4">
                                  <Heart className="w-8 h-8 fill-rose-500 stroke-rose-500" />
                                </div>
                                <h3 className="font-display font-medium text-xl text-white mb-2">
                                  Added to Favorites Archive!
                                </h3>
                                <p className="text-neutral-400 text-xs max-w-xs font-light">
                                  Stylist Agent has saved this outfit structure. Future curations will prioritize this stylistic direction.
                                </p>
                              </motion.div>
                            )}
                          </AnimatePresence>

                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            
                            {/* Left: Metadata details */}
                            <div className="space-y-5">
                              <div>
                                <h4 className="text-[10px] font-mono text-amber-200 uppercase tracking-widest mb-1.5">
                                  SUITE COORDINATION NAME
                                </h4>
                                <h3 className="font-display font-light text-2xl text-white tracking-tight">
                                  {recsQueue[queueIndex].outfitName}
                                </h3>
                              </div>

                              <div>
                                <h4 className="text-[10px] font-mono text-neutral-400 uppercase tracking-wider mb-2">
                                  Stylist Rationale
                                </h4>
                                <p className="text-sm text-neutral-300 font-light leading-relaxed">
                                  {recsQueue[queueIndex].rationale}
                                </p>
                              </div>

                              {/* Chosen Closet items list */}
                              <div>
                                <h4 className="text-[10px] font-mono text-neutral-400 uppercase tracking-wider mb-3">
                                  Suggested Wardrobe Items (Closet Selections)
                                </h4>
	                                <div className="space-y-2">
	                                  {recsQueue[queueIndex].items.map((item, idx) => {
	                                    const fullItemObj = closetItems.find(c => c.id === item.id || c.name === item.name);
                                      const itemImageUrl = item.imageUrl || fullItemObj?.imageUrl;
                                      const itemBuyUrl = item.buyUrl || item.productLink || fullItemObj?.productLink;
	                                    return (
	                                      <div 
	                                        key={idx} 
	                                        className="flex items-center justify-between p-3 bg-neutral-950/80 border border-neutral-850 rounded-xl"
	                                      >
	                                        <div className="flex items-center space-x-3">
	                                          {itemImageUrl ? (
	                                            <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-neutral-900 border border-neutral-800">
	                                              <img 
	                                                src={itemImageUrl} 
	                                                alt={item.name} 
	                                                className="w-full h-full object-cover" 
	                                                referrerPolicy="no-referrer"
                                              />
                                            </div>
                                          ) : (
                                            <div className="w-10 h-10 rounded-lg bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-500 flex-shrink-0">
                                              <Shirt className="w-5 h-5" />
                                            </div>
                                          )}
	                                          <div>
	                                            <p className="text-xs font-medium text-white">{item.name}</p>
	                                            <p className="text-[9px] font-mono text-neutral-450 uppercase">
                                                {[item.brand || fullItemObj?.brand, item.category, item.color || fullItemObj?.color].filter(Boolean).join(" / ")}
                                              </p>
	                                          </div>
	                                        </div>
                                          {itemBuyUrl ? (
                                            <a
                                              href={itemBuyUrl}
                                              target="_blank"
                                              rel="noreferrer"
                                              className="text-[10px] text-amber-200/80 hover:text-amber-100 bg-neutral-900 px-2 py-1 rounded font-mono border border-neutral-850"
                                            >
                                              BUY
                                            </a>
                                          ) : (
                                            <span className="text-[10px] text-neutral-500 bg-neutral-900 px-2 py-0.5 rounded font-mono border border-neutral-850">
                                              ITEM
                                            </span>
                                          )}
	                                      </div>
	                                    );
	                                  })}
                                </div>
                              </div>

                              {/* Supplementary online products */}
                              {recsQueue[queueIndex].onlineSourced && recsQueue[queueIndex].onlineSourced.length > 0 && (
                                <div className="border-t border-neutral-850 pt-4">
                                  <div className="flex items-center space-x-1.5 mb-2.5">
                                    <ShoppingBag className="w-3.5 h-3.5 text-amber-300" />
                                    <h4 className="text-[10px] font-mono text-neutral-400 uppercase tracking-widest">
                                      Supplementary Online Additions (Sourced Fallbacks)
                                    </h4>
                                  </div>
                                  <div className="space-y-2">
	                                    {recsQueue[queueIndex].onlineSourced.map((prod, idx) => (
	                                      <div key={idx} className="p-3 bg-neutral-950/30 border border-neutral-850 rounded-xl">
	                                        <div className="flex justify-between items-start mb-1">
	                                          <p className="text-xs font-medium text-amber-100">{prod.name}</p>
                                            <div className="flex items-center gap-2">
	                                            <span className="text-xs font-mono font-medium text-amber-200">{prod.price}</span>
                                              {(prod.buyUrl || prod.url) && (
                                                <a
                                                  href={prod.buyUrl || prod.url}
                                                  target="_blank"
                                                  rel="noreferrer"
                                                  className="text-[10px] text-neutral-950 bg-amber-200 hover:bg-amber-100 rounded px-2 py-0.5 font-mono"
                                                >
                                                  BUY
                                                </a>
                                              )}
                                            </div>
	                                        </div>
	                                        <p className="text-[11px] text-neutral-400 font-light leading-tight">{prod.reason}</p>
	                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                            </div>

                            {/* Right: Dynamic Try-on rendering area */}
                            <div className="bg-neutral-950/60 rounded-2xl border border-neutral-850 p-5 flex flex-col justify-between">
                              <div>
                                <div className="flex items-center justify-between mb-3.5">
                                  <span className="text-[10px] font-mono text-neutral-450 uppercase tracking-wider">
                                    Silhouette & Try-On Advice
                                  </span>
                                  <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                                </div>
                                <p className="text-xs text-neutral-300 font-light leading-relaxed mb-4 p-3 bg-neutral-950/80 border border-neutral-900 rounded-lg">
                                  {recsQueue[queueIndex].tryOnAdvice}
                                </p>
                              </div>

                              {/* Virtual Try-On Canvas */}
	                              <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-neutral-900 border border-neutral-850 p-2 flex flex-col items-center justify-center text-center self-center max-w-[280px]">
                                {isGeneratingVisual ? (
                                  <div className="p-4 flex flex-col items-center">
                                    <div className="w-8 h-8 rounded-full border-2 border-amber-200 border-t-transparent animate-spin mb-3" />
                                    <p className="text-[10px] text-neutral-400 font-mono uppercase tracking-wide">
                                      Generating photorealistic synthesis...
                                    </p>
                                  </div>
                                ) : generatedVisualUrl ? (
                                  <div className="relative w-full h-full rounded-lg overflow-hidden group">
                                    <img 
                                      src={generatedVisualUrl} 
                                      alt="Generated try-on rendering" 
                                      className="w-full h-full object-cover"
                                      referrerPolicy="no-referrer"
                                    />
                                    {visualError && (
                                      <div className="absolute top-2 left-2 right-2 bg-neutral-950/90 text-[10px] text-neutral-300 py-1 px-2 rounded backdrop-blur">
                                        {visualError}
                                      </div>
                                    )}
                                    <div className="absolute inset-0 bg-neutral-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                      <button 
                                        onClick={() => handleGenerateSyntheticRender(recsQueue[queueIndex])}
                                        className="text-[10px] bg-neutral-950/90 hover:bg-neutral-950 text-white font-mono uppercase border border-neutral-800 px-3 py-1.5 rounded"
                                      >
                                        RE-GENERATE
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="p-4">
                                    <Shirt className="w-10 h-10 text-neutral-600 mx-auto mb-3" />
                                    <h5 className="text-xs font-medium text-white mb-1.5">Synthetic Try-On Canvas</h5>
                                    <p className="text-[10px] text-neutral-450 leading-relaxed mb-4">
                                      The clothing layers will be simulated over your full-body portrait profile. Click to project a gorgeous cinematic look.
                                    </p>
                                    <button
                                      onClick={() => handleGenerateSyntheticRender(recsQueue[queueIndex])}
                                      className="px-4 py-2 bg-neutral-950 hover:bg-neutral-900 border border-neutral-800 text-amber-200 hover:text-white rounded-lg text-[11px] font-mono tracking-wider transition-all"
                                    >
                                      GENERATE AI PORTRAIT Preview
                                    </button>
                                  </div>
	                                )}
	                              </div>
                                <GuardrailPanel guardrail={visualGuardrail} />

	                              {/* Interactive Actions */}
                              <div className="flex space-x-3 mt-6 border-t border-neutral-850 pt-5">
                                <button
                                  onClick={handleDislikeCurrentOutfit}
                                  className="flex-1 py-3 bg-neutral-950 hover:bg-neutral-900 text-rose-400 hover:text-rose-300 font-mono text-[11px] tracking-widest border border-neutral-805 hover:border-rose-955/40 rounded-xl flex items-center justify-center space-x-2 transition-all active:scale-98"
                                >
                                  <ThumbsDown className="w-3.5 h-3.5 stroke-[2px]" />
                                  <span>DISLIKE (SKIP)</span>
                                </button>
                                <button
                                  onClick={() => handleLikeCurrentOutfit(recsQueue[queueIndex])}
                                  className="flex-1 py-3 bg-amber-100 hover:bg-amber-200 text-neutral-950 font-mono text-[11px] tracking-widest rounded-xl flex items-center justify-center space-x-2 transition-all active:scale-98 shadow-md"
                                >
                                  <ThumbsUp className="w-3.5 h-3.5 stroke-[2px]" />
                                  <span>LIKE (FAVORITE)</span>
                                </button>
                              </div>

                            </div>

                          </div>

                        </motion.div>
                      </AnimatePresence>

                    </div>
                  ) : (
                    <div className="border border-neutral-850 bg-neutral-900/10 rounded-3xl p-12 text-center flex flex-col items-center justify-center min-h-[500px]">
                      <div className="bg-neutral-900 border border-neutral-800 p-4 rounded-full mb-4">
                        <RotateCcw className="w-8 h-8 text-neutral-400" />
                      </div>
                      <h3 className="font-display font-light text-xl text-white mb-2">Completed Outerwear Curations</h3>
                      <p className="text-neutral-400 max-w-md mx-auto text-xs leading-relaxed mb-6">
                        You have browsed all 3 custom outfits compiled by the AI Agent. If you didn't find the perfect fit, try modifying Macy's store stock-list items, or modify your style prompts and inspiration choices on the left!
                      </p>
                      <button
                        onClick={requestStylingRecommendations}
                        className="px-6 py-2.5 bg-amber-200 hover:bg-amber-300 text-neutral-950 font-medium rounded-xl text-xs transition"
                      >
                        Re-run Outfit Generator
                      </button>
                    </div>
                  )}

                </div>
              )}

            </div>

          </div>
        )}        {/* MACY'S COOPERATIVE CATALOG STOCKROOM TAB */}
        {activeTab === "closet" && (
          <div className="space-y-8 animate-fadeIn">
            
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-neutral-900 pb-5">
              <div>
                <h1 className="font-display font-light text-3xl text-white">
                  Macy's Store Catalog & Stockroom
                </h1>
                <p className="text-neutral-400 text-xs font-mono uppercase tracking-widest mt-1">
                  BROWSE AND EXPLORE THE ACTIVE CLOTHING INVENTORY SOURCED FROM MACY’S
                </p>
              </div>

              {/* Status information panel cards */}
              <div className="flex items-center space-x-6 text-xs bg-neutral-900/40 border border-neutral-80 w-full md:w-auto p-4 rounded-xl">
                <div>
                  <span className="block text-neutral-500 font-mono uppercase text-[9px]">TOTAL AVAILABLE STOCK</span>
                  <span className="text-lg text-white font-medium">{stockroomTotal || catalogTotal} styles</span>
                  {stockroomItems.length > 0 && stockroomTotal > stockroomItems.length && (
                    <span className="block text-neutral-500 font-mono text-[8px]">{stockroomItems.length} currently shown</span>
                  )}
                </div>
                <div>
                  <span className="block text-neutral-500 font-mono uppercase text-[9px]">TARGET AESTHETICS</span>
                  <span className="text-sm text-amber-200 font-medium">
                    {STYLE_PREF_CHOICES.filter(p => selectedStylesOnboard.includes(p.id)).map(p => p.name).join(", ")}
                  </span>
                </div>
              </div>
            </div>

            {/* Catalog dashboard layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Left Side: Real-time Catalog Filters & Department Search (4 cols) */}
              <div className="lg:col-span-4 space-y-6">
                
                {/* Search & Sliders */}
                <div className="border border-neutral-800 bg-neutral-900/20 rounded-2xl p-5 space-y-5">
                  <div className="flex items-center space-x-2 pb-3 border-b border-neutral-850">
                    <SlidersHorizontal className="w-4 h-4 text-amber-300" />
                    <h3 className="font-display font-medium text-sm text-white uppercase tracking-wider">Catalog Filters</h3>
                  </div>

                  {/* Search bar input constraint */}
                  <div className="space-y-1.5">
                    <label className="block text-[9px] font-mono text-neutral-400 uppercase tracking-widest">
                      Search Macy's Styles
                    </label>
                    <div className="relative">
                      <Search className="absolute left-3 top-2.5 w-4 h-4 text-neutral-500" />
                      <input
                        type="text"
                        placeholder="Search jeans, coat, brand..."
                        value={storeSearchQuery}
                        onChange={(e) => setStoreSearchQuery(e.target.value)}
                        className="w-full bg-neutral-950 border border-neutral-850 rounded-xl py-2 pl-9 pr-3 text-xs text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-amber-400/50 transition-all font-sans"
                      />
                    </div>
                  </div>

                  {/* Department selectors */}
                  <div className="space-y-1.5">
                    <label className="block text-[9px] font-mono text-neutral-400 uppercase tracking-widest">
                      Department Grouping
                    </label>
                    <div className="grid grid-cols-3 gap-1 bg-neutral-950 p-1 border border-neutral-850 rounded-xl">
                      <button
                        onClick={() => setStoreGenderFilter("all")}
                        className={`py-1 rounded-lg text-[10px] font-medium transition-all ${
                          storeGenderFilter === "all"
                            ? "bg-neutral-850 text-white shadow-sm"
                            : "text-neutral-500 hover:text-neutral-350"
                        }`}
                      >
                        All Stock
                      </button>
                      <button
                        onClick={() => setStoreGenderFilter("female")}
                        className={`py-1 rounded-lg text-[10px] font-medium transition-all ${
                          storeGenderFilter === "female"
                            ? "bg-neutral-850 text-amber-200 shadow-sm"
                            : "text-neutral-500 hover:text-neutral-350"
                        }`}
                      >
                        Women's
                      </button>
                      <button
                        onClick={() => setStoreGenderFilter("male")}
                        className={`py-1 rounded-lg text-[10px] font-medium transition-all ${
                          storeGenderFilter === "male"
                            ? "bg-neutral-850 text-amber-200 shadow-sm"
                            : "text-neutral-500 hover:text-neutral-350"
                        }`}
                      >
                        Men's
                      </button>
                    </div>
                  </div>

                  {/* Category selectors vertical list */}
                  <div className="space-y-1.5">
                    <label className="block text-[9px] font-mono text-neutral-400 uppercase tracking-widest">
                      Garment Department
                    </label>
                    <div className="flex flex-col space-y-1">
                      {["all", "Tops", "Bottoms", "Outerwear", "Shoes", "Accessories"].map((cat) => {
                        const count = cat === "all" 
                          ? closetItems.length 
                          : closetItems.filter(i => i.category === cat).length;
                        const isSelect = storeCategoryFilter === cat || (cat === "all" && storeCategoryFilter === "all");
                        return (
                          <button
                            key={cat}
                            onClick={() => setStoreCategoryFilter(cat === "all" ? "all" : cat as GarmentCategory)}
                            className={`flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition border cursor-pointer ${
                              isSelect 
                                ? "bg-gradient-to-r from-amber-400/10 to-yellow-500/10 border-amber-500/30 text-amber-200 font-medium" 
                                : "border-transparent text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
                            }`}
                          >
                            <span>{cat === "all" ? "All Categories" : cat}</span>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-950 text-neutral-500 border border-neutral-855">
                              {count}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Stock quick template injector */}
                  <div className="border-t border-neutral-850 pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono text-neutral-400 uppercase tracking-widest">
                         Macy's Stock Catalog Injector
                      </span>
                      <Info className="w-3 h-3 text-neutral-500" />
                    </div>
                    <p className="text-[10px] text-neutral-500 mb-3 leading-normal">
                      Expand the store's recommendation pool with pre-stylized Macy's partner items instantly:
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {clothingPresets.map((preset, idx) => (
                        <button
                          key={idx}
                          onClick={() => addPresetItem(preset)}
                          className="flex items-center text-left space-x-2 p-1.5 rounded-lg border border-neutral-850 hover:border-amber-400/20 hover:bg-neutral-905 w-full text-[10px] transition-all cursor-pointer"
                        >
                          <img src={preset.image} className="w-7 h-7 rounded object-cover flex-shrink-0" />
                          <div className="truncate">
                            <span className="block font-medium text-neutral-200 truncate">{preset.name}</span>
                            <span className="text-[8px] font-mono text-neutral-500">{preset.category}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                </div>

                {/* MACY'S LIVE SOURCING SCRAPER PLATFORM */}
                <div className="border border-neutral-800 bg-neutral-900/20 rounded-2xl p-5 space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-neutral-850">
                    <div className="flex items-center space-x-2">
                      <Network className="w-4 h-4 text-emerald-400" />
                      <h3 className="font-display font-medium text-sm text-white uppercase tracking-wider">Macy's Live Scraper</h3>
                    </div>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[8px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      ● Active
                    </span>
                  </div>

                  <p className="text-[10px] text-neutral-400 leading-normal">
                    This advanced panel crawls real clothing items active on <strong className="text-white">macys.com</strong> to dynamically expand your fitting advisor's catalog stock.
                  </p>

                  {/* Scraper Selector */}
                  <div className="space-y-2">
                    <label className="block text-[8px] font-mono text-neutral-400 uppercase tracking-widest">
                      Scraping Technique
                    </label>
                    <div className="grid grid-cols-2 gap-1 bg-neutral-950 p-1 border border-neutral-850 rounded-xl">
                      <button
                        onClick={() => {
                          setScraperMode("search");
                          setScraperSuccessMsg(null);
                        }}
                        className={`py-1.5 rounded-lg text-[9px] font-medium transition-all cursor-pointer ${
                          scraperMode === "search"
                            ? "bg-neutral-850 text-white shadow-sm"
                            : "text-neutral-500 hover:text-neutral-350"
                        }`}
                      >
                        Search-Grounded AI
                      </button>
                      <button
                        onClick={() => {
                          setScraperMode("url");
                          setScraperSuccessMsg(null);
                        }}
                        className={`py-1.5 rounded-lg text-[9px] font-medium transition-all cursor-pointer ${
                          scraperMode === "url"
                            ? "bg-neutral-850 text-white shadow-sm"
                            : "text-neutral-500 hover:text-neutral-350"
                        }`}
                      >
                        Direct URL Crawler
                      </button>
                    </div>
                  </div>

                  {/* Dynamic Mode Forms */}
                  {scraperMode === "search" ? (
                    <div className="space-y-1.5">
                      <label className="block text-[8px] font-mono text-neutral-400 uppercase tracking-widest">
                        Category Query Term
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          placeholder="e.g., womens winter coats, designer boots"
                          value={scraperQuery}
                          onChange={(e) => setScraperQuery(e.target.value)}
                          className="w-full bg-neutral-950 border border-neutral-850 rounded-xl py-2 px-3 text-xs text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-emerald-500/50 transition-all"
                        />
                      </div>
                      <span className="block text-[8px] text-neutral-500">
                        Uses live Search Grounding to scrape accurate Macy's catalog listings.
                      </span>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <label className="block text-[8px] font-mono text-neutral-400 uppercase tracking-widest">
                        Macy's Product Catalog URL
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          placeholder="https://www.macys.com/shop/product/..."
                          value={scraperUrl}
                          onChange={(e) => setScraperUrl(e.target.value)}
                          className="w-full bg-neutral-950 border border-neutral-850 rounded-xl py-2 px-3 text-xs text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-emerald-500/50 transition-all font-mono"
                        />
                      </div>
                      <span className="block text-[8px] text-neutral-500">
                        Fetches raw HTML and extracts brand, title, and price tags direct from CDNs.
                      </span>
                    </div>
                  )}

                  {/* Action execution trigger */}
                  <button
                    onClick={handleRunScraper}
                    disabled={isScraping}
                    className={`w-full py-2.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all duration-300 flex items-center justify-center space-x-2 border cursor-pointer ${
                      isScraping
                        ? "bg-neutral-900 border-neutral-800 text-neutral-500 cursor-not-allowed"
                        : "bg-gradient-to-r from-emerald-600 to-teal-600 text-white border-emerald-500/30 hover:shadow-lg hover:shadow-emerald-950/20 hover:border-emerald-400"
                    }`}
                  >
                    {isScraping ? (
                      <>
                        <div className="animate-spin rounded-full h-3.5 w-3.5 border-t-2 border-b-2 border-emerald-400"></div>
                        <span>Crawl Pipeline Running...</span>
                      </>
                    ) : (
                      <>
                        <Globe className="w-3.5 h-3.5 text-emerald-300" />
                        <span>Run Real-Time Scraper</span>
                      </>
                    )}
                  </button>

                  {/* Scraper Success alert banner */}
                  {scraperSuccessMsg && (
                    <div className="p-3 bg-emerald-950/40 border border-emerald-800/40 rounded-xl text-[10px] text-emerald-300 animate-slideUp font-sans leading-relaxed">
                      <strong className="block font-semibold mb-0.5 text-emerald-200">Ingest Synced:</strong>
                      {scraperSuccessMsg}
                    </div>
                  )}

                  {/* Live crawler Terminal/Console Logs */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="block text-[8px] font-mono text-neutral-400 uppercase tracking-widest flex items-center space-x-1">
                        <Terminal className="w-3 h-3 text-neutral-400" />
                        <span>Crawler Socket Console</span>
                      </label>
                      <button 
                        onClick={() => setScraperLogs(["Terminal cleared. Scraper engine ready."])}
                        className="text-[8px] font-mono text-neutral-600 hover:text-neutral-400"
                      >
                        Clear
                      </button>
                    </div>
                    <div className="font-mono bg-black/95 p-3 rounded-xl h-28 overflow-y-auto border border-neutral-850 text-[9px] text-emerald-400 space-y-1 select-none">
                      {scraperLogs.map((log, lidx) => (
                        <div key={lidx} className="leading-relaxed whitespace-pre-wrap break-all border-b border-neutral-900/30 pb-0.5">
                          {log.startsWith("[crawler] [Source") ? (
                            <span className="text-cyan-400">{log}</span>
                          ) : log.includes("[success]") ? (
                            <span className="text-emerald-300 font-bold">{log}</span>
                          ) : log.includes("[critical]") || log.includes("[error]") ? (
                            <span className="text-rose-400">{log}</span>
                          ) : log.includes("[Request]") ? (
                            <span className="text-yellow-300">{log}</span>
                          ) : (
                            <span>{log}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

              </div>

              {/* Right Side: Grid of available clothing stock matching filter choices (8 cols) */}
              <div className="lg:col-span-8">
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  
                  {(() => {
                    const filteredStoreItems = stockroomItems.length > 0 ? stockroomItems : closetItems;

                    if (isStockroomLoading) {
                      return (
                        <div className="col-span-full border border-neutral-850 border-dashed rounded-3xl p-16 text-center flex flex-col items-center justify-center min-h-[400px]">
                          <div className="w-8 h-8 rounded-full border-2 border-amber-200 border-t-transparent animate-spin mb-3" />
                          <span className="text-xs font-mono uppercase tracking-widest text-neutral-400">
                            Loading catalog matches
                          </span>
                        </div>
                      );
                    }

                    if (filteredStoreItems.length === 0) {
                      return (
                        <div className="col-span-full border border-neutral-850 border-dashed rounded-3xl p-16 text-center flex flex-col items-center justify-center min-h-[400px]">
                          <SlidersHorizontal className="w-10 h-10 text-neutral-600 mb-3.5" />
                          <span className="text-xs font-mono uppercase tracking-widest text-neutral-400 mb-1">
                            No Matching Catalog Styles
                          </span>
                          <span className="text-xs text-neutral-600 max-w-sm">
                            {stockroomError || "Try broadening your search text or switching department filters (All stock vs Men's or Women's)."}
                          </span>
                        </div>
                      );
                    }

                    return filteredStoreItems.map((item) => (
                      <div 
                        key={item.id} 
                        className="group relative overflow-hidden rounded-xl border border-neutral-850 bg-neutral-900/25 flex flex-col hover:border-neutral-700 transition"
                      >
                        {/* Garment Image */}
                        <div className="aspect-square bg-neutral-950 overflow-hidden relative border-b border-neutral-900">
                          {item.imageUrl ? (
                            <img 
                              src={item.imageUrl} 
                              alt={item.name} 
                              className="w-full h-full object-cover group-hover:scale-102 transition duration-500"
                              referrerPolicy="no-referrer"
                            />
                          ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center p-4">
                              <Shirt className="w-12 h-12 text-neutral-750" />
                            </div>
                          )}
                          
                          {/* Upper category tags */}
                          <div className="absolute top-2 left-2 flex flex-col gap-1">
                            <span className="text-[8px] font-mono bg-neutral-950/85 text-amber-200 border border-neutral-800 px-1.5 py-0.5 rounded uppercase">
                              {item.category}
                            </span>
                            {item.gender && (
                              <span className="text-[8px] font-mono bg-neutral-950/85 text-white/80 border border-neutral-800 px-1.5 py-0.5 rounded uppercase self-start">
                                {item.gender === "male" ? "MEN" : "WOMEN"}
                              </span>
                            )}
                          </div>

                          {/* Hover Overlay with delete button */}
                          <div className="absolute inset-0 bg-neutral-950/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <button
                              onClick={() => removeClosetItem(item.id)}
                              className="bg-neutral-900 hover:bg-rose-500 text-neutral-300 hover:text-white p-2 text-xs rounded-xl border border-neutral-800 transition shadow-lg pointer flex items-center space-x-1"
                              title="Delete from Catalog"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span className="font-mono text-[9px] uppercase font-bold pr-1">Out of Stock</span>
                            </button>
                          </div>
                        </div>

                        {/* Info lines */}
                        <div className="p-3 bg-neutral-950/20 flex-1 flex flex-col justify-between text-left">
                          <div>
                            <div className="text-[9px] font-semibold text-amber-200 uppercase tracking-widest leading-none mb-1">
                              {item.brand || "Macy's Exclusive"}
                            </div>
                            <p className="text-xs font-semibold text-white tracking-wider line-clamp-1 mb-2">
                              {item.name}
                            </p>
                            <div className="grid grid-cols-2 gap-1 mb-2">
                              <div className="bg-neutral-950/40 p-1 rounded border border-neutral-900 text-left">
                                <span className="block text-[7px] font-mono text-neutral-500 uppercase leading-none">COLOR</span>
                                <span className="text-[9px] text-neutral-300 font-medium truncate block leading-tight">{item.color}</span>
                              </div>
                              <div className="bg-neutral-950/40 p-1 rounded border border-neutral-900 text-left">
                                <span className="block text-[7px] font-mono text-neutral-500 uppercase leading-none">PATTERN</span>
                                <span className="text-[9px] text-neutral-300 font-medium truncate block leading-tight">{item.pattern}</span>
                              </div>
                            </div>
                            <p className="text-[10px] text-neutral-400 font-light leading-snug line-clamp-2">
                              {item.vibe}
                            </p>
                          </div>
                          {item.id.includes("preset-") && (
                            <div className="mt-3 pt-2 border-t border-neutral-900 flex justify-between items-center text-[8px] font-mono">
                              <span className="text-amber-300">SKU ASSOCIATED</span>
                              <span className="text-neutral-500">LIVE</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ));
                  })()}

                </div>

              </div>

            </div>

          </div>
        )}

        {/* MY LIKED STYLES ARCHIVE TAB */}
        {activeTab === "liked" && (
          <div className="space-y-6">
            <div className="border-b border-neutral-900 pb-5">
              <h1 className="font-display font-light text-3xl text-white">
                Favorites & Loved Styling Sets
              </h1>
              <p className="text-neutral-400 text-xs font-mono uppercase tracking-widest mt-1">
                REVIEW STYLIST ARCHIVES AND SUCCESS STRATA
              </p>
            </div>

            {likedOutfits.length === 0 ? (
              <div className="border border-neutral-850 bg-neutral-900/10 rounded-3xl p-12 text-center flex flex-col items-center justify-center min-h-[300px]">
                <Heart className="w-12 h-12 text-neutral-600 mb-4 animate-pulse" />
                <h3 className="font-display font-light text-lg text-white mb-2">
                  Favorites Closet Empty
                </h3>
                <p className="text-neutral-400 max-w-sm mx-auto text-xs leading-relaxed">
                  Go to the "Discover & Try-On" workspace and click **Like** on outfit suggestions you love to archive your styling ideas here.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {likedOutfits.map((outfit) => (
                  <div 
                    key={outfit.id} 
                    className="border border-neutral-800 bg-neutral-900/30 rounded-2xl p-5 md:p-6 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-4 pb-3 border-b border-neutral-850">
                        <div>
                          <h3 className="font-display font-medium text-lg text-white">
                            {outfit.outfitName}
                          </h3>
                          <span className="text-[9px] font-mono text-neutral-400">SAVED ON {outfit.likedAt}</span>
                        </div>
                        <button
                          onClick={() => removeLikedOutfit(outfit.id)}
                          className="text-neutral-500 hover:text-rose-450 text-xs p-1"
                          title="Remove from Loved Sets"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="space-y-3">
                        <div>
                          <span className="block text-[9px] font-mono text-neutral-450 uppercase mb-1">STYLING DECISION RATIONALE:</span>
                          <p className="text-xs text-neutral-350 leading-relaxed font-light">{outfit.rationale}</p>
                        </div>

                        <div>
                          <span className="block text-[9px] font-mono text-neutral-450 uppercase mb-1.5">ASSOCIATES REGISTERED CODES:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {outfit.items.map((itName, idx) => (
                              <span 
                                key={idx} 
                                className="text-[10px] bg-neutral-950 border border-neutral-850 px-2 py-1 rounded text-neutral-305"
                              >
                                {itName}
                              </span>
                            ))}
                          </div>
                        </div>

                        {outfit.onlineSourced && outfit.onlineSourced.length > 0 && (
                          <div className="pt-2">
                            <span className="block text-[9px] font-mono text-neutral-450 uppercase mb-1.5">SUPPLEMENTED PURCHASE RECOMMENDATIONS:</span>
                            <div className="space-y-1.5">
                              {outfit.onlineSourced.map((src, idx) => (
                                <div key={idx} className="p-2 bg-neutral-950 text-[11px] rounded border border-neutral-900 flex justify-between">
                                  <span>{src.name} • <span className="text-neutral-400 font-light">{src.reason}</span></span>
                                  <span className="text-amber-250 font-mono text-xs">{src.price}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="pt-2 border-t border-neutral-900 mt-3">
                          <span className="block text-[9px] font-mono text-lime-400/80 uppercase tracking-widest mb-1">FIT RATING PULL:</span>
                          <p className="text-xs text-neutral-300 font-mono leading-relaxed">{outfit.tryOnAdvice}</p>
                        </div>
                      </div>

                    </div>
                  </div>
                ))}

              </div>
            )}

          </div>
        )}
              {/* EMBEDDED SYSTEM DESIGN DOCUMENT TAB */}
        {activeTab === "designdoc" && (
          <div className="max-w-4xl mx-auto space-y-8 pb-12">
            
            {/* Design Document Title */}
            <div className="text-center py-6 border-b border-neutral-900">
              <div className="inline-flex space-x-2 items-center bg-neutral-900 border border-neutral-800 text-neutral-400 px-3 py-1 rounded-full text-xs font-mono mb-4 tracking-wider">
                <Cpu className="w-3.5 h-3.5 text-amber-300" />
                <span>INTELLIGENCE SPECIFICATION SHEET</span>
              </div>
              <h1 className="font-display font-light text-3xl md:text-4xl text-white">
                Macy's Personal Fitting Advisor System
              </h1>
              <p className="text-neutral-550 font-mono text-xs mt-2 uppercase tracking-widest">
                SYSTEM INTERNALS AND DECISION FLOWS
              </p>
            </div>

            {/* Structured Interactive Wiki */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
              
              <div className="md:col-span-4 space-y-3">
                <div className="sticky top-24 space-y-2 text-xs">
                  <span className="block font-mono text-neutral-500 uppercase tracking-widest mb-2 px-3">DOCUMENT CATALOG</span>
                  {[
                    "1. Executive Architecture",
                    "2. AI Preference Model",
                    "3. Macy's Store Stock Room",
                    "4. Feedback Recommendation Algorithm",
                    "5. Sourced Fallbacks Specs"
                  ].map((cat, idx) => (
                    <div 
                      key={idx} 
                      className="p-3 bg-neutral-900/30 border border-neutral-850 hover:bg-neutral-900 text-neutral-300 hover:text-white rounded-xl cursor-default"
                    >
                      {cat}
                    </div>
                  ))}
                </div>
              </div>

              <div className="md:col-span-8 space-y-8 text-sm text-neutral-300 font-light leading-relaxed">
                
                <section className="space-y-3">
                  <h2 className="font-display font-normal text-xl text-white border-b border-neutral-900 pb-2">
                    1. Executive & Full-Stack Architecture
                  </h2>
                  <p>
                    The system implements a robust **Express API server + Vite client** architecture. To shield the Gemini API key from client-side bundles (adhering to strict sandbox credentials mandates), all `@google/genai` calls occur within the Node.js backend (`server.ts`).
                  </p>
                  <p>
                    Communication is driven through large-payload `POST` endpoints. Customer style vectors, optional reference inspiration photos, skin undertones, and event prompts are securely parsed in server-side memory to formulate custom styling directions.
                  </p>
                </section>

                <section className="space-y-3">
                  <h2 className="font-display font-normal text-xl text-white border-b border-neutral-900 pb-2">
                    2. AI Aesthetic Preference Modeling (Onboarding)
                  </h2>
                  <p>
                    To resolve the "cold-start" styled paradox when users first sit in the Fitting Suite, the program executes an onboarding sequence mapping key style archetypes. The user's selections compile an **Aesthetic Preference Vector** injected to guide the recommendation generator.
                  </p>
                  <p>
                    Pointers such as *"Minimalist Casual"* translate to strict negative contrast limits, neutral tone scales, and classic silhouette weights. Pointers like *"Streetwear"* trigger calculations advocating oversized cuts and utilitarian accents.
                  </p>
                </section>

                <section className="space-y-3">
                  <h2 className="font-display font-normal text-xl text-white border-b border-neutral-900 pb-2">
                    3. Macy's Active Store Inventory Database
                  </h2>
                  <p>
                    Instead of arbitrary private garments uploads, the Advisor searches an active store stock catalog curated specifically from Macy's collection (featuring renowned partner labels like Alfani, Calvin Klein, Michael Kors, Charter Club, Levi's, and Tommy Hilfiger).
                  </p>
                  <p>
                    The item matrix records brand associations, gender divisions (Men's vs Women's collection), material attributes, and dominant color shades, ensuring exact-match coordination on the sales floor.
                  </p>
                </section>

                <section className="space-y-3">
                  <h2 className="font-display font-normal text-xl text-white border-b border-neutral-900 pb-2">
                    4. State-Authoritative Recommendation Engine
                  </h2>
                  <p>
                    We leverage the server-side `@google/genai` SDK using `gemini-2.5-flash`. The model cross-references Macy's available store inventory, filters matching gender segments, incorporates body-palette constraints, and suggests exactly three custom coordinated outfits.
                  </p>
                  <p>
                    Instead of return lists, suggestions are presented as interactive flashcards. Customers can either add items to their **Favorites**, or click **Dislike** to transition smoothly to the next suggestion.
                  </p>
                </section>

                <section className="space-y-3">
                  <h2 className="font-display font-normal text-xl text-white border-b border-neutral-900 pb-2">
                    5. Sourced Fallbacks Specs
                  </h2>
                  <p>
                    If the store catalog shows stock gaps (such as missing specific accessories or pairs of shoes), the prompt matrix triggers supplementary merchandise sourcing recommendations.
                  </p>
                  <p>
                    This is returned with style guidelines, specific brand details, and coordination tips to ensure staff can find the best alternatives from nearby shelves.
                  </p>
                </section>

              </div>

            </div>

          </div>
        )}

      </main>

      {/* FOOTER METADATA MARGIN */}
      <footer className="mt-12 py-8 border-t border-neutral-900 text-center text-xs text-neutral-500 font-mono">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>© 2026 Macy's Personal Fitting Advisor. Sourced and compiled via Google GenAI.</p>
        </div>
      </footer>

    </div>
  );
}
