"""Generate local credentials without printing or overwriting them."""
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / '.env'
if path.exists():
    print('.env already exists; preserved.')
else:
    with path.open('x', encoding='utf-8') as f:
        f.write(f'POSTGRES_PASSWORD={secrets.token_hex(24)}\nDEMO_PASSWORD={secrets.token_hex(24)}\nAPI_PORT=8030\n')
    path.chmod(0o600)
    print('Created .env; credentials remain local.')
