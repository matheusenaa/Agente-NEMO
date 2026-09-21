#!/usr/bin/env python
"""
Script de validação e teste dos 10 principais modelos do OpenRouter.
Executa verificações de autenticação, cabeçalhos, integridade de slugs e respostas dos modelos.
"""

import sys
import os

# Garante suporte a UTF-8 no terminal do Windows (PowerShell/CMD)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
from pathlib import Path
from typing import List

# Garante que a raiz do projeto esteja no sys.path independente do ambiente
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from models_config import get_all_models, ModelInfo
from openrouter_client import OpenRouterClient, CompletionResult

console = Console(force_terminal=True, legacy_windows=False)


def print_banner():
    title = Text("NEMO • OpenRouter Multi-Model Test Suite", style="bold cyan")
    subtitle = Text("Validação dos 10 Principais Modelos de IA via OpenRouter API", style="italic white")
    panel = Panel.fit(
        Text.assemble(title, "\n", subtitle),
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 4)
    )
    console.print(panel)

def display_auth_status(client: OpenRouterClient) -> bool:
    """Verifica e exibe o status de autenticação."""
    if not client.has_valid_key_format():
        console.print(
            Panel(
                "[bold yellow][ATENCAO] Chave de API OPENROUTER_API_KEY nao configurada![/bold yellow]\n\n"
                "Para executar chamadas reais aos modelos, siga os passos:\n"
                "1. Obtenha sua chave em: [bold underline cyan]https://openrouter.ai/keys[/bold underline cyan]\n"
                "2. Abra o arquivo [bold green].env[/bold green] neste diretorio e substitua:\n"
                "   [dim]OPENROUTER_API_KEY=sua_chave_aqui[/dim] por [bold]OPENROUTER_API_KEY=sk-or-v1-...[/bold]\n"
                "3. Execute este teste novamente.",
                title="[bold yellow]Configuracao Requerida[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED
            )
        )
        return False

    auth_info = client.check_auth()
    if not auth_info.get("valid"):
        console.print(
            Panel(
                f"[bold red][ERRO] Falha de Autenticacao na API OpenRouter:[/bold red]\n"
                f"{auth_info.get('error')}\n\n"
                "Verifique se a chave no arquivo [bold].env[/bold] esta correta e ativa.",
                title="[bold red]Erro de Autenticacao[/bold red]",
                border_style="red"
            )
        )
        return False

    label = auth_info.get("label") or "Chave Padrão"
    usage = auth_info.get("usage", 0.0)
    limit = auth_info.get("limit") or "Sem limite"
    is_free = "Sim" if auth_info.get("is_free_tier") else "Não"

    console.print(
        f"[bold green][OK] Autenticado com sucesso no OpenRouter![/bold green] "
        f"[dim](Label: {label} | Uso: ${usage} | Limite: ${limit} | Free Tier: {is_free})[/dim]\n"
    )
    return True

def run_catalog_check(client: OpenRouterClient, models: List[ModelInfo]):
    """Valida o mapeamento dos slugs frente ao catálogo atual do OpenRouter."""
    live_models = client.get_live_models()
    console.print(f"[bold cyan][INFO] Catalogo ao Vivo:[/bold cyan] {len(live_models)} modelos ativos detectados no OpenRouter.")

    table = Table(
        title="Mapeamento de Modelos e Slugs Ativos",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=True
    )
    table.add_column("#", justify="center", style="dim", width=4)
    table.add_column("Provedor", style="bold", width=12)
    table.add_column("Modelo", width=22)
    table.add_column("Slug Primario", width=34)
    table.add_column("Status no Catalogo", justify="center", width=18)
    table.add_column("Slug Efetivo", width=34)

    for i, m in enumerate(models, 1):
        is_exact = m.primary_slug in live_models
        resolved_slug, is_fallback = client.resolve_model_slug(m)

        if is_exact:
            status_text = "[green]● Ativo Exato[/green]"
            effective = f"[green]{m.primary_slug}[/green]"
        elif is_fallback:
            status_text = "[yellow]▲ Fallback Ativo[/yellow]"
            effective = f"[yellow]{resolved_slug}[/yellow]"
        else:
            status_text = "[dim]○ Direto (API)[/dim]"
            effective = m.primary_slug

        table.add_row(
            str(i),
            m.provider,
            m.name,
            m.primary_slug,
            status_text,
            effective
        )

    console.print(table)
    console.print()

def run_tests(
    client: OpenRouterClient,
    models: List[ModelInfo],
    prompt: str = "Responda apenas 'OK' e o seu nome de modelo"
):
    """Executa o prompt de validação em cada um dos 10 modelos."""
    console.print(f"[bold blue][START] Iniciando testes com o prompt:[/bold blue] [italic]\"{prompt}\"[/italic]\n")

    results_table = Table(
        title="Resultados dos Testes com os 10 Modelos OpenRouter",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True
    )
    results_table.add_column("#", justify="center", width=4)
    results_table.add_column("Provedor", width=12)
    results_table.add_column("Modelo", width=22)
    results_table.add_column("Slug Utilizado", width=32)
    results_table.add_column("Status", justify="center", width=14)
    results_table.add_column("Latencia", justify="right", width=12)
    results_table.add_column("Tokens (P/C)", justify="center", width=14)
    results_table.add_column("Resposta do Modelo", width=35)

    success_count = 0
    fallback_count = 0
    error_count = 0
    latencies = []
    total_tokens_consumed = 0

    for idx, model_info in enumerate(models, 1):
        console.print(f"[{idx}/10] Testando [bold]{model_info.provider} - {model_info.name}[/bold]...", end=" ")

        result: CompletionResult = client.test_single_model(model_info, prompt=prompt)

        if result.success:
            success_count += 1
            latencies.append(result.latency_ms)
            total_tokens_consumed += result.total_tokens

            if result.is_fallback:
                fallback_count += 1
                status_str = "[yellow][FALLBACK][/yellow]"
                console.print(f"[yellow]OK (Fallback: {result.model_used}) em {result.latency_ms:.0f}ms[/yellow]")
            else:
                status_str = "[green][OK][/green]"
                console.print(f"[green]OK em {result.latency_ms:.0f}ms[/green]")

            token_str = f"{result.prompt_tokens}/{result.completion_tokens}"
            # Limpa resposta para exibição em uma linha
            cleaned_response = " ".join(result.content.split())
            if len(cleaned_response) > 35:
                cleaned_response = cleaned_response[:32] + "..."

            results_table.add_row(
                str(idx),
                model_info.provider,
                model_info.name,
                result.model_used,
                status_str,
                f"{result.latency_ms:.0f} ms",
                token_str,
                f"[italic]{cleaned_response}[/italic]"
            )
        else:
            error_count += 1
            console.print(f"[red]FALHA[/red]")
            err_msg = result.error_message or "Erro desconhecido"
            if len(err_msg) > 35:
                err_msg = err_msg[:32] + "..."

            results_table.add_row(
                str(idx),
                model_info.provider,
                model_info.name,
                result.model_used,
                "[red][ERRO][/red]",
                "-",
                "-",
                f"[red]{err_msg}[/red]"
            )

    console.print()
    console.print(results_table)

    # Estatísticas Finais
    avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    summary_text = (
        f"Total Testados: [bold]{len(models)}[/bold] | "
        f"Sucesso: [bold green]{success_count}[/bold green] | "
        f"Fallback Ativo: [bold yellow]{fallback_count}[/bold yellow] | "
        f"Falhas: [bold red]{error_count}[/bold red]\n"
        f"Latência Média: [bold]{avg_latency:.1f} ms[/bold] | "
        f"Tokens Totais Consumidos: [bold]{total_tokens_consumed}[/bold]"
    )
    console.print(
        Panel(
            summary_text,
            title="[bold]Resumo da Execução[/bold]",
            border_style="green" if error_count == 0 else "yellow",
            box=box.ROUNDED
        )
    )

def main():
    parser = argparse.ArgumentParser(description="Validação de modelos OpenRouter.")
    parser.add_argument(
        "--prompt",
        type=str,
        default="Responda apenas 'OK' e o seu nome de modelo",
        help="Prompt de verificação a ser enviado aos modelos."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="ID ou slug de um modelo específico para testar individualmente."
    )
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Apenas valida a integridade dos slugs com o catálogo ao vivo sem realizar chamadas de LLM."
    )
    args = parser.parse_args()

    print_banner()

    client = OpenRouterClient()
    models = get_all_models()

    if args.model:
        filtered = [m for m in models if m.id == args.model or m.primary_slug == args.model]
        if not filtered:
            console.print(f"[bold red]Modelo '{args.model}' não encontrado na lista configurada![/bold red]")
            sys.exit(1)
        models = filtered

    # 1. Validação de Catálogo e Mapeamento de Slugs
    run_catalog_check(client, models)

    if args.catalog_only:
        console.print("[green]Validação de catálogo concluída com sucesso.[/green]")
        return

    # 2. Verificação de Autenticação
    has_auth = display_auth_status(client)
    if not has_auth:
        console.print(
            "\n[dim]Dica: Para validar o mapeamento de slugs sem chave de API, use:[/] "
            "[bold cyan]python test_openrouter.py --catalog-only[/bold cyan]\n"
        )
        sys.exit(0)

    # 3. Execução dos Testes com os Modelos
    run_tests(client, models, prompt=args.prompt)

if __name__ == "__main__":
    main()
