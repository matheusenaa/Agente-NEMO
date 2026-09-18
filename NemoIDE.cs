using System;
using System.Diagnostics;
using System.IO;

class NemoIDE {
    static void Main() {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        
        Console.Title = "NEMO IDE Launcher";
        Console.WriteLine("==========================================");
        Console.WriteLine("  NEMO IDE - Iniciando componentes...");
        Console.WriteLine("==========================================");
        Console.WriteLine();

        // 1. Backend
        Console.WriteLine("[1/3] Iniciando backend FastAPI (porta 8798)...");
        string backendArgs = "/k \"cd /d \\\"" + root + "\\\" && python -c \\\"import sys; sys.path.insert(0, r'" + root + "'); import nemo_server as ns; import uvicorn; uvicorn.run(ns.app, host=ns.DEFAULT_HOST, port=ns.DEFAULT_PORT, log_level='info')\\\"\"";
        var backend = new Process {
            StartInfo = new ProcessStartInfo {
                FileName = "cmd.exe",
                Arguments = backendArgs,
                WorkingDirectory = root,
                UseShellExecute = true,
                WindowStyle = ProcessWindowStyle.Normal
            }
        };
        backend.Start();
        Console.WriteLine("      Backend iniciado em janela separada.");

        // Aguardar backend subir
        Console.WriteLine("[2/3] Aguardando backend subir (5s)...");
        System.Threading.Thread.Sleep(5000);

        // 2. Frontend
        Console.WriteLine("[3/3] Iniciando frontend dev server (porta 5173)...");
        string dashDir = Path.Combine(root, "dashboard");
        string frontendArgs = "/k \"cd /d \\\"" + dashDir + "\\\" && npm run dev\"";
        var frontend = new Process {
            StartInfo = new ProcessStartInfo {
                FileName = "cmd.exe",
                Arguments = frontendArgs,
                WorkingDirectory = dashDir,
                UseShellExecute = true,
                WindowStyle = ProcessWindowStyle.Normal
            }
        };
        frontend.Start();
        Console.WriteLine("      Frontend iniciado em janela separada.");

        // 3. Abrir navegador
        Console.WriteLine();
        Console.WriteLine("Abrindo navegador em http://localhost:5173/ ...");
        try {
            Process.Start(new ProcessStartInfo("http://localhost:5173/") { UseShellExecute = true });
        } catch {
            Console.WriteLine("   (Nao foi possivel abrir o navegador automaticamente)");
        }

        Console.WriteLine();
        Console.WriteLine("NEMO IDE rodando!");
        Console.WriteLine("- Backend: janela 'NEMO Backend' (porta 8798)");
        Console.WriteLine("- Frontend: janela 'NEMO Dashboard' (porta 5173)");
        Console.WriteLine("- Navegador: http://localhost:5173/");
        Console.WriteLine();
        Console.WriteLine("Pressione qualquer tecla para encerrar este launcher (as outras janelas continuam abertas).");
        Console.ReadKey();
    }
}