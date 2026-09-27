import { useEffect, useState, useCallback } from "react";
import { Capacitor } from "@capacitor/core";
import { Network } from "@capacitor/network";
import { LocalNotifications } from "@capacitor/local-notifications";
import { Haptics, ImpactStyle } from "@capacitor/haptics";
import { StatusBar, Style } from "@capacitor/status-bar";
import { SplashScreen } from "@capacitor/splash-screen";
import { Keyboard } from "@capacitor/keyboard";
import { PushNotifications } from "@capacitor/push-notifications";

export const isNative = Capacitor.isNativePlatform();
export const platform = Capacitor.getPlatform();

export function useCapacitor() {
  const [networkStatus, setNetworkStatus] = useState<"online" | "offline" | "unknown">("unknown");

  useEffect(() => {
    if (!isNative) return;

    const setupNetwork = async () => {
      const status = await Network.getStatus();
      setNetworkStatus(status.connected ? "online" : "offline");

      const listener = await Network.addListener("networkStatusChange", (status) => {
        setNetworkStatus(status.connected ? "online" : "offline");
      });

      return listener;
    };

    let listener: any;
    setupNetwork().then((l) => { listener = l; });

    return () => {
      if (listener) listener.remove();
    };
  }, [isNative]);

  const requestPermissions = useCallback(async () => {
    if (!isNative) return;

    await LocalNotifications.requestPermissions();
    await PushNotifications.requestPermissions();
  }, [isNative]);

  const haptic = useCallback(async (style: "light" | "medium" | "heavy" = "medium") => {
    if (!isNative) return;
    await Haptics.impact({ style: style as ImpactStyle });
  }, [isNative]);

  const showSplashScreen = useCallback(async () => {
    if (!isNative) return;
    await SplashScreen.show({ autoHide: false });
  }, [isNative]);

  const hideSplashScreen = useCallback(async () => {
    if (!isNative) return;
    await SplashScreen.hide();
  }, [isNative]);

  const setStatusBarStyle = useCallback(async (dark: boolean) => {
    if (!isNative) return;
    await StatusBar.setStyle({ style: dark ? Style.Dark : Style.Light });
  }, [isNative]);

  const setKeyboardResize = useCallback(async (mode: "body" | "ionic" | "native") => {
    if (!isNative) return;
    await Keyboard.setResizeMode({ mode: mode as any });
  }, [isNative]);

  const scheduleLocalNotification = useCallback(async (
    title: string,
    body: string,
    at: Date,
    extra?: any
  ) => {
    if (!isNative) return;
    await LocalNotifications.schedule({
      notifications: [{
        title,
        body,
        id: Date.now(),
        schedule: { at },
        extra,
        sound: "default",
        actionTypeId: "",
        attachments: [],
      }],
    });
  }, [isNative]);

  return {
    isNative,
    platform,
    networkStatus,
    requestPermissions,
    haptic,
    showSplashScreen,
    hideSplashScreen,
    setStatusBarStyle,
    setKeyboardResize,
    scheduleLocalNotification,
  };
}

export function useMobileSync(
  onSync: () => Promise<void>,
  intervalMs = 30000
) {
  const { networkStatus, isNative } = useCapacitor();

  useEffect(() => {
    if (!isNative) return;

    let timer: ReturnType<typeof setInterval>;

    const runSync = async () => {
      if (networkStatus === "online") {
        try {
          await onSync();
        } catch {}
      }
    };

    timer = setInterval(runSync, intervalMs);
    runSync();

    return () => clearInterval(timer);
  }, [onSync, intervalMs, networkStatus, isNative]);
}

export function useAppLifecycle(
  onPause: () => void,
  onResume: () => void
) {
  useEffect(() => {
    if (!isNative) return;

    const handlePause = () => onPause();
    const handleResume = () => onResume();

    document.addEventListener("pause", handlePause);
    document.addEventListener("resume", handleResume);

    return () => {
      document.removeEventListener("pause", handlePause);
      document.removeEventListener("resume", handleResume);
    };
  }, [onPause, onResume, isNative]);
}