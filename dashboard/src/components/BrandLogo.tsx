import { BRAND } from "@/config/branding";

type Size = "sm" | "md" | "lg" | "xl";

interface Props {
  size?: Size;
  /** Texto alternativo. Vazio oculta a imagem de leitores de tela. */
  alt?: string;
  className?: string;
  /** true = versão reduzida (header/sidebar), sem slogan. */
  compact?: boolean;
  /** Desativa o carregamento preguiçoso (usado no login/splash, que é o primeiro paint). */
  priority?: boolean;
}

const DIM: Record<Size, number> = {
  sm: 28,
  md: 44,
  lg: 96,
  xl: 160,
};

/**
 * Logo oficial do SYNOP.
 *
 * Usa <picture> com WebP + fallback JPEG e cai para o emoji da marca se o
 * asset não carregar (ex.: cache antigo do service worker ou CDN ainda sem
 * o arquivo). Assim a identidade nunca some da interface.
 */
export function BrandLogo({ size = "md", alt = BRAND.name, className, compact = false, priority = false }: Props) {
  const px = DIM[size];
  return (
    <picture className={className}>
      <source srcSet={BRAND.assets.logoWebp} type="image/webp" />
      <img
        src={BRAND.assets.logoJpg}
        alt={alt}
        width={px}
        height={px}
        loading={priority ? "eager" : "lazy"}
        decoding="async"
        {...(priority ? { fetchPriority: "high" as const } : {})}
        onError={(e) => {
          // Fallback: se o arquivo não existir/expirar, mostra o emoji da marca.
          const img = e.currentTarget;
          if (img.dataset.fallbackApplied) return;
          img.dataset.fallbackApplied = "1";
          img.src =
            "data:image/svg+xml," +
            encodeURIComponent(
              `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>${BRAND.icons.logo}</text></svg>`
            );
        }}
        style={{ width: px, height: px, objectFit: "contain", display: "block" }}
      />
      {!compact && alt ? <span className="sr-only">{alt}</span> : null}
    </picture>
  );
}

export default BrandLogo;
