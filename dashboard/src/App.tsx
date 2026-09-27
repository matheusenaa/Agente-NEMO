import { useEffect } from "react";
import { AppShell } from "@/components/ide/AppShell";
import { useIdeStore } from "@/store/useIdeStore";
import { getAgent } from "@/data/agents";
import { OfflineProvider } from "@/lib/offline/OfflineProvider";
import { useCapacitor, useAppLifecycle, isNative } from "@/lib/offline";

export function App() {
  const { hideSplashScreen, setStatusBarStyle, setKeyboardResize, requestPermissions } = useCapacitor();

  useEffect(() => {
    const timer = setTimeout(() => {
      const nemo = getAgent("nemo");
      useIdeStore.getState().notify({
        icon: nemo.icon,
        text: `NEMO IDE ${isNative ? "mobile" : "online"} — ${nemo.name} pronto para trabalhar`,
        tone: "ok",
      });
      hideSplashScreen();
    }, 600);
    return () => clearTimeout(timer);
  }, [hideSplashScreen]);

  useEffect(() => {
    if (isNative) {
      setStatusBarStyle(true);
      setKeyboardResize("body");
      requestPermissions();
    }
  }, [isNative, setStatusBarStyle, setKeyboardResize, requestPermissions]);

  useAppLifecycle(
    () => console.log("[NEMO] App paused"),
    () => console.log("[NEMO] App resumed")
  );

  return (
    <OfflineProvider>
      <AppShell />
    </OfflineProvider>
  );
}