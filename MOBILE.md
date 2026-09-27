# NEMO — Guia Mobile (Capacitor)

## Visão Geral

O NEMO usa **Capacitor** para gerar aplicativos nativos iOS e Android a partir do código web (React + Vite), mantendo 100% do código compartilhado com a versão PWA.

## Arquitetura Mobile

```
┌─────────────────────────────────────────────────────────────┐
│                     NEMO MOBILE                              │
├─────────────────────────────────────────────────────────────┤
│  Web Code (React + Vite) ──▶ Capacitor ──▶ Native Apps      │
│       │                              │                      │
│       │                              ├──────────────────┐  │
│       │                              ▼                  ▼  │
│       │                    ┌─────────────┐        ┌─────────────┐
│       │                    │   Android   │        │     iOS     │
│       │                    │  (Kotlin)   │        │  (Swift)    │
│       │                    └─────────────┘        └─────────────┘
│       │                              │                  │
│       ▼                              ▼                  ▼
│  ┌─────────────┐            ┌─────────────┐    ┌─────────────┐
│  │   Shared    │            │  Capacitor  │    │  Capacitor  │
│  │  Web Code   │◀──────────▶│   Plugins   │    │   Plugins   │
│  └─────────────┘            └─────────────┘    └─────────────┘
└─────────────────────────────────────────────────────────────┘
```

## Configuração Atual

### capacitor.config.ts
```typescript
{
  appId: 'com.nemo.ide',
  appName: 'NEMO IDE',
  webDir: 'dist',
  server: { androidScheme: 'https' },
  android: {
    buildOptions: { keystorePath: undefined }, // Debug build
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: true,
  },
  ios: {
    contentInset: 'automatic',
    scrollEnabled: true,
    limitsNavigationsToAppBoundDomains: false,
  },
  plugins: {
    SplashScreen: { launchShowDuration: 2000, backgroundColor: '#0f0a14' },
    StatusBar: { style: 'dark', backgroundColor: '#0f0a14' },
    Keyboard: { resize: 'body', style: 'dark' },
    LocalNotifications: { iconColor: '#0b6e4f' },
    PushNotifications: { presentationOptions: ['badge', 'sound', 'alert'] },
  }
}
```

### Plugins Instalados

| Plugin | Finalidade | Config |
|--------|-----------|--------|
| `@capacitor/splash-screen` | Tela de splash | 2s, dark theme |
| `@capacitor/status-bar` | Status bar | Dark, overlay |
| `@capacitor/keyboard` | Teclado virtual | Resize body |
| `@capacitor/local-notifications` | Notificações locais | Lembretes, tasks |
| `@capacitor/push-notifications` | Push notifications | FCM/APNs |
| `@capacitor/haptics` | Feedback tátil | Botões, ações |
| `@capacitor/network` | Detecção rede | Online/offline nativo |

## Pré-requisitos

### Android
- **Android Studio** (latest)
- **JDK 17+**
- **Android SDK** (API 33+)
- **Dispositivo/Emulador** com Android 7.0+ (API 24+)

### iOS (apenas macOS)
- **Xcode 15+**
- **iOS 15+** deployment target
- **Apple Developer Account** (para device/build distribution)
- **CocoaPods** (`sudo gem install cocoapods`)

### Comum
- **Node.js 18+**
- **Capacitor CLI** (`npm install -g @capacitor/cli`)

## Build & Deploy

### Desenvolvimento

```bash
# 1. Build do frontend
cd dashboard
npm run build

# 2. Sincroniza com projetos nativos
npx cap sync

# 3. Abre no Android Studio
npx cap open android

# 4. Abre no Xcode (macOS)
npx cap open ios
```

### Android - Debug APK

```bash
# Via Gradle (linha de comando)
cd dashboard/android
./gradlew assembleDebug

# Output: android/app/build/outputs/apk/debug/app-debug.apk

# Instala no dispositivo conectado
./gradlew installDebug

# Ou via adb
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Android - Release AAB (Play Store)

```bash
# 1. Configurar keystore (uma vez)
# Edite android/app/build.gradle:
# signingConfigs {
#   release {
#     keyAlias 'nemo'
#     keyPassword 'sua_senha'
#     storeFile file('nemo-release.keystore')
#     storePassword 'sua_senha'
#   }
# }

# 2. Gerar keystore
keytool -genkey -v -keystore nemo-release.keystore \
  -alias nemo -keyalg RSA -keysize 2048 -validity 10000

# 3. Build release
cd dashboard/android
./gradlew bundleRelease

# Output: android/app/build/outputs/bundle/release/app-release.aab
```

### iOS - Debug (Simulador)

```bash
# 1. Abre no Xcode
npx cap open ios

# 2. No Xcode:
# - Selecione simulador (iPhone 15 Pro)
# - Product → Run (Cmd+R)
```

### iOS - Release (App Store)

```bash
# 1. No Xcode:
# - Selecione "Any iOS Device (arm64)"
# - Product → Archive
# - Window → Organizer → Distribute App

# 2. Configurar no Xcode:
# - Team: sua Apple Developer Team
# - Bundle Identifier: com.nemo.ide
# - Signing: Automatically manage signing
# - Capabilities: Push Notifications, Background Modes

# 3. App Store Connect:
# - Criar app com bundle ID com.nemo.ide
# - Upload via Transporter ou Xcode
# - TestFlight → Testes internos/externos
# - Submeter para review
```

## Funcionalidades Mobile Específicas

### 1. Detecção de Rede Nativa

```typescript
// dashboard/src/hooks/useCapacitor.ts
import { Network } from '@capacitor/network';

const status = await Network.getStatus();
// { connected: true, connectionType: 'wifi' }

Network.addListener('networkStatusChange', (status) => {
  // Atualiza UI automaticamente
});
```

### 2. Notificações Locais

```typescript
import { LocalNotifications } from '@capacitor/local-notifications';

// Solicita permissão (iOS)
await LocalNotifications.requestPermissions();

// Agenda lembrete
await LocalNotifications.schedule({
  notifications: [{
    title: 'Lembrete NEMO',
    body: 'Reunião às 14:00',
    id: Date.now(),
    schedule: { at: new Date('2026-01-15T14:00:00') },
    sound: 'default',
  }]
});
```

### 3. Push Notifications (FCM/APNs)

```typescript
import { PushNotifications } from '@capacitor/push-notifications';

// Registro
await PushNotifications.requestPermissions();
await PushNotifications.register();

// Listeners
PushNotifications.addListener('registration', (token) => {
  // Envie token.value para seu backend
  api.savePushToken(token.value);
});

PushNotifications.addListener('pushNotificationReceived', (notification) => {
  // App em foreground
  showInAppNotification(notification);
});
```

**Backend necessário:** Firebase Cloud Messaging (Android) + APNs (iOS)

### 4. Haptics (Feedback Tátil)

```typescript
import { Haptics, ImpactStyle } from '@capacitor/haptics';

// Botão pressionado
await Haptics.impact({ style: ImpactStyle.Light });

// Ação concluída
await Haptics.impact({ style: ImpactStyle.Medium });

// Erro
await Haptics.impact({ style: ImpactStyle.Heavy });
```

### 5. Ciclo de Vida do App

```typescript
import { useAppLifecycle } from '@/lib/offline';

useAppLifecycle(
  () => { /* App pausado - salva estado */ },
  () => { /* App retomado - sync se online */ }
);

// Eventos nativos:
// 'pause' - App vai para background
// 'resume' - App volta para foreground
```

### 6. Splash Screen Personalizada

```xml
<!-- android/app/src/main/res/drawable/splash.xml -->
<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
  <item android:drawable="@color/splash_bg"/>
  <item>
    <bitmap android:gravity="center" android:src="@drawable/splash_icon"/>
  </item>
</layer-list>

<!-- colors.xml -->
<color name="splash_bg">#0f0a14</color>
```

### 7. Ícones Adaptativos (Android)

```bash
# Gere ícones adaptativos
# Coloque em android/app/src/main/res/mipmap-*/
# ic_launcher.xml (foreground + background)
# ic_launcher_round.xml
```

```xml
<!-- ic_launcher.xml -->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
  <background android:drawable="@color/ic_launcher_background"/>
  <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
```

## Build CI/CD (GitHub Actions)

### Android

```yaml
# .github/workflows/android.yml
name: Android Build
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: 'temurin', java-version: '17' }
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: 'dashboard/package-lock.json' }
      - run: cd dashboard && npm ci && npm run build
      - run: npx cap sync android
      - run: cd dashboard/android && ./gradlew assembleDebug
      - uses: actions/upload-artifact@v4
        with: { name: 'apk-debug', path: 'dashboard/android/app/build/outputs/apk/debug/*.apk' }
```

### iOS (requer macOS runner)

```yaml
# .github/workflows/ios.yml
name: iOS Build
on: [push]
jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: cd dashboard && npm ci && npm run build
      - run: npx cap sync ios
      - run: cd dashboard/ios/App && xcodebuild -workspace App.xcworkspace -scheme App -configuration Release -destination generic/platform=iOS -archivePath build/App.xcarchive archive
      - uses: actions/upload-artifact@v4
        with: { name: 'ios-archive', path: 'dashboard/ios/App/build/App.xcarchive' }
```

## Testes Mobile

### Android - Device Farm / Test Lab

```bash
# Firebase Test Lab
gcloud firebase test android run \
  --type instrumentation \
  --app dashboard/android/app/build/outputs/apk/debug/app-debug.apk \
  --test dashboard/android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk \
  --device model=Pixel6,version=33,locale=en,orientation=portrait
```

### Testes Manuais Checklist

| Área | Testes |
|------|--------|
| **Instalação** | APK/AAB instala, abre sem crash |
| **Splash** | Mostra 2s, transição suave |
| **Login** | Email/senha, OAuth Google, biometria |
| **Navegação** | Tabs, drawer, back gesture |
| **Chat** | Digita, envia, recebe, scroll |
| **Escritório 2D** | Phaser renderiza, touch funciona |
| **Teclado** | Não cobre inputs, resize correto |
| **Notificações** | Local + Push (se configurado) |
| **Offline** | Desliga Wi-Fi, cria task, reconecta, sync |
| **Orientação** | Portrait/landscape, safe areas |
| **Background** | Pause/resume, estado preservado |
| **Performance** | 60fps, memória < 150MB |
| **Permissões** | Solicita no momento certo |

## Problemas Comuns

| Problema | Solução |
|----------|---------|
| `cap sync` falha | `npm run build` primeiro, verifique `webDir: 'dist'` |
| Android: `INSTALL_FAILED_VERSION_DOWNGRADE` | Desinstale app anterior: `adb uninstall com.nemo.ide` |
| iOS: `Signing certificate not found` | Xcode → Signing & Capabilities → Team |
| Push não chega | Verifique `google-services.json` (Android) / `GoogleService-Info.plist` (iOS) |
| Teclado cobre input | `Keyboard.setResizeMode({ mode: 'body' })` |
| Splash não aparece | Verifique `SplashScreen.launchShowDuration` |
| Safe area iOS | CSS: `padding-top: env(safe-area-inset-top)` |
| Back gesture Android | Não intercepta navegação do app |

## Permissões Android (android/app/src/main/AndroidManifest.xml)

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.VIBRATE" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
```

## Permissões iOS (ios/App/App/Info.plist)

```xml
<key>NSAppTransportSecurity</key>
<dict>
  <key>NSAllowsArbitraryLoads</key>
  <true/>
</dict>
<key>UIBackgroundModes</key>
<array>
  <string>remote-notification</string>
  <string>fetch</string>
</array>
<key>NSCameraUsageDescription</key>
<string>NEMO precisa acessar a câmera para...</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>NEMO precisa acessar fotos para...</string>
```

## Próximos Passos

- [ ] Configurar Firebase/APNs para Push Notifications
- [ ] Implementar Biometric Auth (FaceID/TouchID)
- [ ] App Shortcuts (long press icon)
- [ ] Widget iOS / Android
- [ ] Deep Links / Universal Links
- [ ] In-App Updates (Play Core / App Store)
- [ ] Crashlytics / Sentry mobile