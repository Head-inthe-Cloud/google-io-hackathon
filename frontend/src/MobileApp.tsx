import { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  Shirt,
  Heart,
  Search,
  Loader2,
  ChevronLeft,
  ShoppingBag,
  Check,
  X,
  ExternalLink,
  Wand2,
} from "lucide-react";
import { STYLE_PREF_CHOICES } from "./data";
import type { ClosetItem, OutfitRecommendation, SourcedProduct } from "./types";
import * as api from "./api";

type Tab = "style" | "shop" | "saved";
type Gender = "female" | "male" | "unisex";

interface SavedOutfit {
  id: string;
  outfitName: string;
  rationale: string;
  items: string[];
  onlineSourced: SourcedProduct[];
  tryOnAdvice: string;
  likedAt: string;
}

const STORAGE_LIKED = "mobile_liked_outfits";
const STORAGE_STYLES = "mobile_selected_styles";
const STORAGE_GENDER = "mobile_gender";
const STORAGE_PROMPT = "mobile_last_prompt";

const OCCASION_QUICK = [
  "Coffee with friends",
  "Date night",
  "Office day",
  "Weekend brunch",
  "Workout",
  "Travel day",
];

const CATEGORY_FILTERS = ["All", "Tops", "Bottoms", "Outerwear", "Shoes", "Accessories"];

function loadLiked(): SavedOutfit[] {
  try {
    const raw = localStorage.getItem(STORAGE_LIKED);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function persistLiked(outfits: SavedOutfit[]) {
  try {
    localStorage.setItem(STORAGE_LIKED, JSON.stringify(outfits));
  } catch {
    /* ignore quota */
  }
}

export default function MobileApp() {
  const [tab, setTab] = useState<Tab>("style");

  // Style screen state
  const [gender, setGender] = useState<Gender>(() => {
    return (localStorage.getItem(STORAGE_GENDER) as Gender) || "female";
  });
  const [selectedStyles, setSelectedStyles] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_STYLES);
      return raw ? JSON.parse(raw) : ["minimalist"];
    } catch {
      return ["minimalist"];
    }
  });
  const [prompt, setPrompt] = useState<string>(() => localStorage.getItem(STORAGE_PROMPT) || "");
  const [recs, setRecs] = useState<OutfitRecommendation[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [recsError, setRecsError] = useState<string | null>(null);

  // Shop screen state
  const [shopItems, setShopItems] = useState<ClosetItem[]>([]);
  const [shopLoading, setShopLoading] = useState(false);
  const [shopError, setShopError] = useState<string | null>(null);
  const [shopCategory, setShopCategory] = useState<string>("All");
  const [shopSearch, setShopSearch] = useState<string>("");
  const [shopSearchDraft, setShopSearchDraft] = useState<string>("");

  // Saved
  const [liked, setLiked] = useState<SavedOutfit[]>(loadLiked);

  // Item detail modal (used from Shop)
  const [detailItem, setDetailItem] = useState<ClosetItem | null>(null);

  // Persist user preferences
  useEffect(() => localStorage.setItem(STORAGE_GENDER, gender), [gender]);
  useEffect(() => localStorage.setItem(STORAGE_STYLES, JSON.stringify(selectedStyles)), [selectedStyles]);
  useEffect(() => localStorage.setItem(STORAGE_PROMPT, prompt), [prompt]);
  useEffect(() => persistLiked(liked), [liked]);

  // Fetch shop items when category/search/gender changes
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setShopLoading(true);
      setShopError(null);
      try {
        const data = await api.fetchCatalog({
          gender: gender === "male" ? "mens" : gender === "female" ? "womens" : undefined,
          category: shopCategory === "All" ? undefined : shopCategory,
          search: shopSearch || undefined,
          limit: 40,
        });
        if (cancelled) return;
        setShopItems(data.items.map(api.catalogItemToClosetItem));
      } catch (e: any) {
        if (cancelled) return;
        setShopError(e?.message || "Could not load catalog");
      } finally {
        if (!cancelled) setShopLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [gender, shopCategory, shopSearch]);

  const toggleStyle = (id: string) => {
    setSelectedStyles((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleStyleMe = useCallback(async () => {
    if (selectedStyles.length === 0 && !prompt.trim()) {
      setRecsError("Pick at least one style or type what you're going for.");
      return;
    }
    setRecsLoading(true);
    setRecsError(null);
    setRecs([]);
    try {
      const profile = await api.buildPreferenceProfile({
        preferences: selectedStyles,
        selfieDescription: "",
        prompt: prompt || "A great-looking outfit for everyday",
        gender,
      });
      const result = await api.getRecommendations({
        preferences: selectedStyles,
        prompt: prompt || "A great-looking outfit for everyday",
        selfieDescription: "",
        preferenceProfile: profile.preferenceProfile,
        gender,
      });
      setRecs(result.recommendations || []);
    } catch (e: any) {
      setRecsError(e?.message || "Recommendation failed");
    } finally {
      setRecsLoading(false);
    }
  }, [selectedStyles, prompt, gender]);

  const isLiked = (outfit: OutfitRecommendation) =>
    liked.some((l) => l.outfitName === outfit.outfitName);

  const toggleLike = (outfit: OutfitRecommendation) => {
    if (isLiked(outfit)) {
      setLiked((prev) => prev.filter((l) => l.outfitName !== outfit.outfitName));
      return;
    }
    const saved: SavedOutfit = {
      id: `${Date.now()}-${outfit.outfitName}`,
      outfitName: outfit.outfitName,
      rationale: outfit.rationale,
      items: outfit.items.map((i) => i.name),
      onlineSourced: outfit.onlineSourced || [],
      tryOnAdvice: outfit.tryOnAdvice,
      likedAt: new Date().toISOString(),
    };
    setLiked((prev) => [saved, ...prev]);
  };

  const removeLiked = (id: string) =>
    setLiked((prev) => prev.filter((l) => l.id !== id));

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans flex flex-col">
      <TopBar tab={tab} liked={liked.length} />

      <main className="flex-1 overflow-y-auto pb-24">
        {tab === "style" && (
          <StyleScreen
            gender={gender}
            setGender={setGender}
            selectedStyles={selectedStyles}
            toggleStyle={toggleStyle}
            prompt={prompt}
            setPrompt={setPrompt}
            onStyleMe={handleStyleMe}
            loading={recsLoading}
            error={recsError}
            recs={recs}
            isLiked={isLiked}
            toggleLike={toggleLike}
          />
        )}
        {tab === "shop" && (
          <ShopScreen
            items={shopItems}
            loading={shopLoading}
            error={shopError}
            category={shopCategory}
            setCategory={setShopCategory}
            searchDraft={shopSearchDraft}
            setSearchDraft={setShopSearchDraft}
            onSearchSubmit={() => setShopSearch(shopSearchDraft.trim())}
            onClearSearch={() => {
              setShopSearchDraft("");
              setShopSearch("");
            }}
            onItem={setDetailItem}
          />
        )}
        {tab === "saved" && (
          <SavedScreen liked={liked} onRemove={removeLiked} />
        )}
      </main>

      <BottomNav tab={tab} setTab={setTab} likedCount={liked.length} />

      {detailItem && (
        <ItemDetailSheet item={detailItem} onClose={() => setDetailItem(null)} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Layout components
// ---------------------------------------------------------------------------

function TopBar({ tab, liked }: { tab: Tab; liked: number }) {
  const title =
    tab === "style" ? "Style Me" : tab === "shop" ? "Shop" : "Saved Looks";
  return (
    <header className="sticky top-0 z-30 bg-neutral-950/95 backdrop-blur border-b border-neutral-800">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl gemini-gradient-bg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-display font-semibold text-neutral-100 leading-tight">
              {title}
            </h1>
            <p className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
              ClosetAI · Mobile
            </p>
          </div>
        </div>
        {tab !== "saved" && liked > 0 && (
          <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-neutral-900 border border-neutral-800">
            <Heart className="w-3 h-3 fill-rose-400 text-rose-400" />
            <span className="text-xs font-mono text-neutral-200">{liked}</span>
          </div>
        )}
      </div>
    </header>
  );
}

function BottomNav({
  tab,
  setTab,
  likedCount,
}: {
  tab: Tab;
  setTab: (t: Tab) => void;
  likedCount: number;
}) {
  const items: Array<{ id: Tab; label: string; icon: typeof Sparkles; badge?: number }> = [
    { id: "style", label: "Style", icon: Wand2 },
    { id: "shop", label: "Shop", icon: ShoppingBag },
    { id: "saved", label: "Saved", icon: Heart, badge: likedCount },
  ];

  return (
    <nav className="fixed bottom-0 inset-x-0 z-40 bg-neutral-950/95 backdrop-blur border-t border-neutral-800 pb-[max(env(safe-area-inset-bottom),0.5rem)]">
      <div className="grid grid-cols-3">
        {items.map(({ id, label, icon: Icon, badge }) => {
          const active = tab === id;
          return (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex flex-col items-center justify-center py-2.5 gap-1 transition-colors active:bg-neutral-900 ${
                active ? "text-amber-200" : "text-neutral-500"
              }`}
            >
              <div className="relative">
                <Icon
                  className={`w-5 h-5 ${active ? "" : ""}`}
                  strokeWidth={active ? 2.4 : 1.8}
                />
                {badge !== undefined && badge > 0 && (
                  <span className="absolute -top-1.5 -right-2 min-w-[16px] h-[16px] px-1 rounded-full bg-rose-500 text-white text-[9px] font-mono flex items-center justify-center">
                    {badge > 99 ? "99+" : badge}
                  </span>
                )}
              </div>
              <span className="text-[10px] font-mono uppercase tracking-wider">
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Style screen
// ---------------------------------------------------------------------------

function StyleScreen({
  gender,
  setGender,
  selectedStyles,
  toggleStyle,
  prompt,
  setPrompt,
  onStyleMe,
  loading,
  error,
  recs,
  isLiked,
  toggleLike,
}: {
  gender: Gender;
  setGender: (g: Gender) => void;
  selectedStyles: string[];
  toggleStyle: (id: string) => void;
  prompt: string;
  setPrompt: (s: string) => void;
  onStyleMe: () => void;
  loading: boolean;
  error: string | null;
  recs: OutfitRecommendation[];
  isLiked: (o: OutfitRecommendation) => boolean;
  toggleLike: (o: OutfitRecommendation) => void;
}) {
  return (
    <div className="px-4 py-4 space-y-5">
      {/* Gender segmented */}
      <section>
        <SectionLabel>I'm shopping for</SectionLabel>
        <div className="grid grid-cols-3 gap-2 p-1 bg-neutral-900 rounded-2xl border border-neutral-800">
          {(["female", "male", "unisex"] as Gender[]).map((g) => (
            <button
              key={g}
              onClick={() => setGender(g)}
              className={`py-2 rounded-xl text-sm font-medium capitalize transition-all ${
                gender === g
                  ? "gemini-gradient-bg text-white shadow"
                  : "text-neutral-400"
              }`}
            >
              {g === "female" ? "Women" : g === "male" ? "Men" : "All"}
            </button>
          ))}
        </div>
      </section>

      {/* Style chips */}
      <section>
        <SectionLabel>Pick a vibe</SectionLabel>
        <div className="flex flex-wrap gap-2">
          {STYLE_PREF_CHOICES.map((s) => {
            const active = selectedStyles.includes(s.id);
            return (
              <button
                key={s.id}
                onClick={() => toggleStyle(s.id)}
                className={`px-3.5 py-2 rounded-full text-xs font-medium border transition-all flex items-center gap-1.5 ${
                  active
                    ? "bg-amber-200 border-amber-200 text-white"
                    : "bg-neutral-900 border-neutral-800 text-neutral-300"
                }`}
              >
                {active && <Check className="w-3 h-3" />}
                {s.chineseName}
              </button>
            );
          })}
        </div>
      </section>

      {/* Quick occasion prompts */}
      <section>
        <SectionLabel>Where are you headed?</SectionLabel>
        <div className="space-y-2">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. dinner at a wine bar, rainy commute, outdoor wedding…"
            rows={2}
            className="w-full px-3 py-2.5 rounded-2xl bg-neutral-900 border border-neutral-800 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-200"
          />
          <div className="flex gap-2 overflow-x-auto -mx-4 px-4 pb-1 scrollbar-none">
            {OCCASION_QUICK.map((q) => (
              <button
                key={q}
                onClick={() => setPrompt(q)}
                className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs bg-neutral-900 border border-neutral-800 text-neutral-400 active:bg-neutral-850"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <button
        onClick={onStyleMe}
        disabled={loading}
        className="w-full py-4 rounded-2xl gemini-gradient-bg text-white font-display font-semibold text-base flex items-center justify-center gap-2 shadow-lg disabled:opacity-60 active:scale-[0.99] transition-transform"
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Styling…
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            Style Me
          </>
        )}
      </button>

      {error && (
        <div className="px-3 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Results */}
      {recs.length > 0 && (
        <section className="pt-2">
          <SectionLabel>Outfits for you</SectionLabel>
          <div className="space-y-4">
            {recs.map((rec, i) => (
              <OutfitCard
                key={`${rec.outfitName}-${i}`}
                outfit={rec}
                liked={isLiked(rec)}
                onLike={() => toggleLike(rec)}
              />
            ))}
          </div>
        </section>
      )}

      {!recs.length && !loading && (
        <div className="text-center py-8 text-neutral-500 text-xs">
          Tap <span className="text-amber-200 font-semibold">Style Me</span> when you're ready.
        </div>
      )}
    </div>
  );
}

function OutfitCard({
  outfit,
  liked,
  onLike,
}: {
  key?: string;
  outfit: OutfitRecommendation;
  liked: boolean;
  onLike: () => void;
}) {
  const firstImage = outfit.items.find((i) => i.imageUrl)?.imageUrl;
  return (
    <article className="rounded-3xl overflow-hidden bg-neutral-900 border border-neutral-800 shadow-sm">
      {firstImage && (
        <div className="relative aspect-[4/3] bg-neutral-850 overflow-hidden">
          <img
            src={firstImage}
            alt={outfit.outfitName}
            className="w-full h-full object-cover"
            loading="lazy"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
          <button
            onClick={onLike}
            className={`absolute top-3 right-3 w-10 h-10 rounded-full backdrop-blur flex items-center justify-center transition-all ${
              liked ? "bg-rose-500 text-white" : "bg-white/80 text-neutral-100"
            }`}
            aria-label={liked ? "Unlike" : "Like"}
          >
            <Heart className={`w-5 h-5 ${liked ? "fill-white" : ""}`} />
          </button>
          <div className="absolute bottom-3 left-3 right-3">
            <h3 className="text-white font-display text-lg font-semibold leading-tight drop-shadow">
              {outfit.outfitName}
            </h3>
          </div>
        </div>
      )}

      <div className="p-4 space-y-3">
        {!firstImage && (
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-base font-display font-semibold text-neutral-100">
              {outfit.outfitName}
            </h3>
            <button
              onClick={onLike}
              className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${
                liked ? "bg-rose-500 text-white" : "bg-neutral-850 text-neutral-300"
              }`}
            >
              <Heart className={`w-4 h-4 ${liked ? "fill-white" : ""}`} />
            </button>
          </div>
        )}

        <p className="text-sm text-neutral-300 leading-relaxed">{outfit.rationale}</p>

        {outfit.items.length > 0 && (
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-neutral-500 mb-2">
              The pieces
            </p>
            <ul className="space-y-1.5">
              {outfit.items.map((item, idx) => (
                <li
                  key={`${item.id || item.name}-${idx}`}
                  className="flex items-start gap-2 text-xs text-neutral-200"
                >
                  <span className="mt-1 w-1 h-1 rounded-full bg-amber-200 flex-shrink-0" />
                  <span>
                    <span className="font-medium">{item.name}</span>
                    {item.category && (
                      <span className="text-neutral-500"> · {item.category}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {outfit.onlineSourced && outfit.onlineSourced.length > 0 && (
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-neutral-500 mb-2">
              Where to shop
            </p>
            <div className="space-y-1.5">
              {outfit.onlineSourced.slice(0, 3).map((p, idx) => (
                <a
                  key={`${p.name}-${idx}`}
                  href={p.buyUrl || p.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-neutral-850 border border-neutral-800 active:bg-neutral-800"
                >
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-neutral-100 truncate">{p.name}</p>
                    <p className="text-[10px] text-neutral-500">{p.price}</p>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
                </a>
              ))}
            </div>
          </div>
        )}

        {outfit.tryOnAdvice && (
          <p className="text-[11px] italic text-neutral-450 leading-relaxed border-t border-neutral-800 pt-3">
            {outfit.tryOnAdvice}
          </p>
        )}
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Shop screen
// ---------------------------------------------------------------------------

function ShopScreen({
  items,
  loading,
  error,
  category,
  setCategory,
  searchDraft,
  setSearchDraft,
  onSearchSubmit,
  onClearSearch,
  onItem,
}: {
  items: ClosetItem[];
  loading: boolean;
  error: string | null;
  category: string;
  setCategory: (c: string) => void;
  searchDraft: string;
  setSearchDraft: (s: string) => void;
  onSearchSubmit: () => void;
  onClearSearch: () => void;
  onItem: (i: ClosetItem) => void;
}) {
  return (
    <div className="flex flex-col">
      {/* Search */}
      <div className="px-4 pt-3 pb-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSearchSubmit();
          }}
          className="relative"
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500 pointer-events-none" />
          <input
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder="Search the catalog"
            className="w-full pl-9 pr-9 py-2.5 rounded-2xl bg-neutral-900 border border-neutral-800 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-200"
          />
          {searchDraft && (
            <button
              type="button"
              onClick={onClearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center text-neutral-500"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </form>
      </div>

      {/* Category pills */}
      <div className="flex gap-2 overflow-x-auto px-4 py-2 scrollbar-none">
        {CATEGORY_FILTERS.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              category === c
                ? "bg-amber-200 border-amber-200 text-white"
                : "bg-neutral-900 border-neutral-800 text-neutral-400"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Results grid */}
      <div className="px-4 pt-3">
        {error && (
          <div className="px-3 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 mb-3">
            {error}
          </div>
        )}

        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-neutral-500 text-sm gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading catalog…
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-neutral-500 text-sm">
            No items match your filters.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => onItem(item)}
                className="text-left rounded-2xl overflow-hidden bg-neutral-900 border border-neutral-800 active:scale-[0.98] transition-transform"
              >
                <div className="aspect-square bg-neutral-850 overflow-hidden">
                  {item.imageUrl ? (
                    <img
                      src={item.imageUrl}
                      alt={item.name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-neutral-700">
                      <Shirt className="w-8 h-8" />
                    </div>
                  )}
                </div>
                <div className="p-2.5">
                  <p className="text-xs font-medium text-neutral-100 line-clamp-2 leading-snug">
                    {item.name}
                  </p>
                  <p className="text-[10px] text-neutral-500 mt-1 truncate">
                    {item.brand} · {item.color}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ItemDetailSheet({ item, onClose }: { item: ClosetItem; onClose: () => void }) {
  // Lock background scroll while open
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-neutral-950">
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
        <button
          onClick={onClose}
          className="flex items-center gap-1 text-neutral-300 text-sm font-medium active:opacity-70"
        >
          <ChevronLeft className="w-5 h-5" />
          Back
        </button>
        <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
          Item Detail
        </span>
        <div className="w-12" />
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="aspect-square bg-neutral-900">
          {item.imageUrl ? (
            <img src={item.imageUrl} alt={item.name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-neutral-700">
              <Shirt className="w-12 h-12" />
            </div>
          )}
        </div>

        <div className="p-4 space-y-3">
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-neutral-500">
              {item.brand}
            </p>
            <h2 className="text-lg font-display font-semibold text-neutral-100 mt-1">
              {item.name}
            </h2>
          </div>

          <div className="flex flex-wrap gap-1.5">
            <Pill>{item.category}</Pill>
            <Pill>{item.color}</Pill>
            {item.pattern && <Pill>{item.pattern}</Pill>}
          </div>

          {item.vibe && (
            <p className="text-sm text-neutral-300 leading-relaxed">{item.vibe}</p>
          )}

          {item.productLink && (
            <a
              href={item.productLink}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center py-3 rounded-2xl gemini-gradient-bg text-white font-medium text-sm"
            >
              View on store
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Saved screen
// ---------------------------------------------------------------------------

function SavedScreen({
  liked,
  onRemove,
}: {
  liked: SavedOutfit[];
  onRemove: (id: string) => void;
}) {
  if (liked.length === 0) {
    return (
      <div className="px-4 py-16 flex flex-col items-center text-center gap-3">
        <div className="w-16 h-16 rounded-3xl bg-neutral-900 border border-neutral-800 flex items-center justify-center">
          <Heart className="w-7 h-7 text-neutral-700" />
        </div>
        <p className="text-sm text-neutral-400 max-w-[240px]">
          Like outfits from the <span className="text-amber-200 font-semibold">Style</span> tab to save them here.
        </p>
      </div>
    );
  }

  return (
    <div className="px-4 py-4 space-y-3">
      {liked.map((o) => (
        <article
          key={o.id}
          className="rounded-2xl bg-neutral-900 border border-neutral-800 p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-base font-display font-semibold text-neutral-100 leading-tight">
                {o.outfitName}
              </h3>
              <p className="text-[10px] font-mono uppercase tracking-wider text-neutral-500 mt-1">
                Saved {new Date(o.likedAt).toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={() => onRemove(o.id)}
              className="w-9 h-9 rounded-full bg-neutral-850 flex items-center justify-center text-neutral-400 active:bg-neutral-800 flex-shrink-0"
              aria-label="Remove"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <p className="text-sm text-neutral-300 mt-2 leading-relaxed">{o.rationale}</p>

          {o.items.length > 0 && (
            <ul className="mt-3 space-y-1">
              {o.items.map((name, i) => (
                <li key={`${name}-${i}`} className="flex items-start gap-2 text-xs text-neutral-300">
                  <span className="mt-1 w-1 h-1 rounded-full bg-amber-200 flex-shrink-0" />
                  <span>{name}</span>
                </li>
              ))}
            </ul>
          )}

          {o.onlineSourced && o.onlineSourced.length > 0 && (
            <div className="mt-3 space-y-1.5">
              {o.onlineSourced.slice(0, 2).map((p, i) => (
                <a
                  key={`${p.name}-${i}`}
                  href={p.buyUrl || p.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-neutral-850 border border-neutral-800"
                >
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-neutral-100 truncate">{p.name}</p>
                    <p className="text-[10px] text-neutral-500">{p.price}</p>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
                </a>
              ))}
            </div>
          )}
        </article>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tiny shared bits
// ---------------------------------------------------------------------------

function SectionLabel({ children }: { children: any }) {
  return (
    <p className="text-[10px] font-mono uppercase tracking-wider text-neutral-500 mb-2">
      {children}
    </p>
  );
}

function Pill({ children }: { children: any }) {
  return (
    <span className="px-2.5 py-1 rounded-full bg-neutral-850 border border-neutral-800 text-[10px] font-mono uppercase tracking-wider text-neutral-300">
      {children}
    </span>
  );
}
