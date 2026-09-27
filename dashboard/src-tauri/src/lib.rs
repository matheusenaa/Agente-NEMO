// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new()
            .with_shortcut("ctrl+shift+s")?.with_handler(|app| {
                if let Some(window) = app.get_webview_window("main") {
                    window.show().ok();
                    window.set_focus().ok();
                }
            })
            .build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .setup(|app| {
            #[cfg(debug_assertions)]
            {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Debug)
                        .build(),
                )?;
            }

            // Configura atalhos globais
            let shortcut = tauri_plugin_global_shortcut::Shortcut::new("ctrl+shift+s")?;
            app.handle().plugin(tauri_plugin_global_shortcut::Builder::new()
                .with_shortcuts(vec![shortcut])?
                .with_handler(|app, shortcut, _event| {
                    if shortcut.matches(tauri_plugin_global_shortcut::Shortcut::new("ctrl+shift+s")?) {
                        if let Some(window) = app.get_webview_window("main") {
                            window.show().ok();
                            window.set_focus().ok();
                        }
                    }
                })
                .build())?;

            // Configura notificações
            let _ = tauri_plugin_notification::init();

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            get_app_info,
            check_updates,
            install_update
        ])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Olá, {}! Bem-vindo ao SYNOP.", name)
}

#[tauri::command]
fn get_app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "SYNOP",
        "version": env!("CARGO_PKG_VERSION"),
        "description": "Inteligência que organiza o seu amanhã",
        "platform": std::env::consts::OS,
    })
}

#[tauri::command]
async fn check_updates(app: tauri::AppHandle) -> Result<tauri_plugin_updater::Update, String> {
    let updater = app.updater().map_err(|e| e.to_string())?;
    let update = updater.check().await.map_err(|e| e.to_string())?;
    Ok(update)
}

#[tauri::command]
async fn install_update(app: tauri::AppHandle) -> Result<(), String> {
    let updater = app.updater().map_err(|e| e.to_string())?;
    updater.download_and_install(|_chunk_length, _content_length| {}, || {}).await.map_err(|e| e.to_string())?;
    Ok(())
}