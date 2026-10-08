"""Generate local credentials without printing or overwriting them."""
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / '.env'
if path.exists():
    if not any(line.startswith('SIMULATOR_SECRET=') for line in path.read_text().splitlines()):
        with path.open('a', encoding='utf-8') as f:
            f.write(f'\nSIMULATOR_SECRET={secrets.token_hex(24)}\n')
    print('.env credentials preserved; missing simulator secret generated.')
else:
    with path.open('x', encoding='utf-8') as f:
        f.write(f'POSTGRES_PASSWORD={secrets.token_hex(24)}\nDEMO_PASSWORD={secrets.token_hex(24)}\nSIMULATOR_SECRET={secrets.token_hex(24)}\nAPI_PORT=8030\n')
    path.chmod(0o600)
    print('Created .env; credentials remain local.')
