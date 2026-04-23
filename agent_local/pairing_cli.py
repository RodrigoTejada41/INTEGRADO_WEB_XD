from __future__ import annotations

from agent_local.pairing.service import PairingRequest, PairingService


def main() -> None:
    print("=== MoviSync Vinculacao (CLI) ===")
    print("Informe a URL da API, nao o codigo de vinculacao.")
    api_base_url = input("URL da API [https://movisystecnologia.com.br/admin/api]: ").strip() or (
        "https://movisystecnologia.com.br/admin/api"
    )
    pairing_code = input("Codigo de vinculacao: ").strip()
    if not pairing_code:
        raise SystemExit("Codigo de vinculacao obrigatorio.")
    empresa_id = input("Empresa ID (opcional): ").strip()
    device_label = input("Dispositivo [loja-01]: ").strip() or "loja-01"
    api_key_file = input("Arquivo da chave [agent_local/data/agent_api_key.txt]: ").strip() or (
        "agent_local/data/agent_api_key.txt"
    )
    env_file = input("Arquivo .env [.env]: ").strip() or ".env"

    try:
        result = PairingService().activate(
            PairingRequest(
                api_base_url=api_base_url,
                pairing_code=pairing_code,
                device_label=device_label,
                empresa_id=empresa_id,
                api_key_file=api_key_file,
                env_file=env_file,
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Falha na vinculacao: {exc}") from exc

    print("")
    print("Vinculacao concluida.")
    print(f"empresa_id={result.empresa_id}")
    print(f"api_key_file={result.api_key_file}")
    print(f"env_file={result.env_file}")


if __name__ == "__main__":
    main()
