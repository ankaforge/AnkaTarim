# Anka Tarimsal Takip

## Yerel geliştirme kurulumu

Gereksinimler:

- Python 3.12 veya üzeri
- Node.js 20.19+ veya 22.12+
- npm
- PostgreSQL 15+ (yerelde Docker ile çalıştırılabilir)

### Veritabanı (PostgreSQL)

Proje kökündeki `docker-compose.yml` ile yerel bir PostgreSQL başlatın:

```powershell
docker compose up -d
```

Docker kullanmıyorsanız kendi PostgreSQL sunucunuzda `anka_tarim` adında bir veritabanı oluşturun.

### Backend (Django API)

Proje kök klasöründe PowerShell açıp sanal ortamı oluşturun ve bağımlılıkları yükleyin:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Veritabanı adresini tanımlayın ve backend'i başlatın:

```powershell
$env:DATABASE_URL = "postgres://anka:anka@127.0.0.1:5432/anka_tarim"
Set-Location backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

`DATABASE_URL` tanımlı değilse backend başlamaz. API, `http://127.0.0.1:8000/api/` adresinde çalışır. Production ortam değişkenleri için `backend\.env.example` dosyasına bakın.

### Frontend (React/Vite)

Backend çalışır durumdayken, proje kökünde ikinci bir PowerShell açın:

```powershell
Set-Location frontend
npm install
npm run dev
```

Arayüzü Vite'ın çıktısında belirtilen yerel adreste açın (varsayılan: `http://localhost:5173`). Geliştirme modunda frontend API adresi varsayılan olarak `http://127.0.0.1:8000/api/` şeklindedir.

API adresini değiştirmek gerekiyorsa `frontend\.env.local` dosyasına aşağıdaki satırı ekleyin ve Vite'ı yeniden başlatın:

```dotenv
VITE_API_URL=http://127.0.0.1:8000/api/
```
