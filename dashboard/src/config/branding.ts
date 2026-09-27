/**
 * SYNOP — Configuração centralizada de identidade visual da marca.
 * 
 * Este arquivo centraliza todos os textos, nomes e identidades da marca SYNOP.
 * Altere aqui para propagar a identidade em toda a aplicação.
 * 
 * IMPORTANTE: Referências internas técnicas (backend, DB, APIs, agent IDs)
 * NÃO devem ser alteradas aqui — elas permanecem como "NEMO" por compatibilidade.
 */

export const BRAND = {
  // Nome público da plataforma
  name: "SYNOP",
  
  // Nome curto (para uso em espaços reduzidos)
  shortName: "SYNOP",
  
  // Descrição/slogan principal
  slogan: "Inteligência que organiza o seu amanhã",
  
  // Descrição longa (para metadata, PWA, etc.)
  description: "Plataforma inteligente de agentes de IA para organização pessoal e profissional",
  
  // Versão da marca (para cache busting de assets)
  version: "1.0.0",
  
  // Cores da marca (referência para CSS/design)
  colors: {
    primary: "#0066cc",      // Azul principal
    secondary: "#00ccff",    // Ciano
    accent: "#cf1126",       // Vermelho Vasco (herança visual)
    dark: "#0f0a14",         // Fundo escuro
    light: "#ffffff",        // Texto claro
  },
  
  // Ícones/emojis associados
  icons: {
    logo: "🧠",              // Emoji fallback para logo
    favicon: "🧠",           // Favicon fallback
    loading: "⚡",           // Loading indicator
  },
  
  // Configurações PWA
  pwa: {
    name: "SYNOP",
    shortName: "SYNOP",
    description: "Plataforma inteligente de agentes de IA",
    themeColor: "#0066cc",
    backgroundColor: "#0f0a14",
    display: "standalone",
    orientation: "portrait-primary",
  },
  
  // Configurações Mobile/Capacitor
  mobile: {
    appId: "com.synop.ide",
    appName: "SYNOP",
    scheme: "synop",
  },
  
  // Configurações Desktop
  desktop: {
    appName: "SYNOP",
    executableName: "SYNOP",
    windowTitle: "SYNOP — Inteligência que organiza o seu amanhã",
  },
  
  // Textos de interface pública
  ui: {
    appTitle: "SYNOP",
    appSubtitle: "Inteligência que organiza o seu amanhã",
    loginTitle: "SYNOP",
    loginSubtitle: "Inteligência que organiza o seu amanhã",
    dashboardTitle: "SYNOP — Dashboard",
    headerBrand: "SYNOP",
    headerSubtitle: "INTELLIGENT AI PLATFORM",
    loadingText: "Carregando SYNOP...",
    offlineText: "SYNOP — Modo offline",
    errorTitle: "SYNOP — Erro",
    shareTitle: "SYNOP",
    shareDescription: "Plataforma inteligente de agentes de IA",
  },
  
  // Textos específicos da tela de login
  login: {
    title: "SYNOP",
    subtitle: "Inteligência que organiza o seu amanhã",
    emailPlaceholder: "E-mail",
    passwordPlaceholder: "Senha",
    submitButton: "Entrar",
    forgotPassword: "Esqueci a senha",
    noAccount: "Não tem conta?",
    signUp: "Criar conta",
    socialLogin: "Ou continue com",
    loading: "Entrando no SYNOP...",
    errorInvalid: "E-mail ou senha incorretos",
    errorNetwork: "Sem conexão. Verifique sua internet.",
  },
} as const;

// Tipos para type safety
export type BrandConfig = typeof BRAND;

// Helper para acessar configurações com fallback seguro
export function getBrand<K extends keyof BrandConfig>(key: K): BrandConfig[K] {
  return BRAND[key];
}

// Exportar também como objeto padrão para compatibilidade
export default BRAND;