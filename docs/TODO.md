# Anka Tarım — Yeniden Yapılandırma TODO

> Hedef: [GEREKSINIMLER.md](GEREKSINIMLER.md). Mevcut özellikler korunacak; sistem çok şirketli, rol bazlı, paket (modül) bazlı ve üründen bağımsız hale getirilecek.
> Hazırlanma: 2026-10-26

---

## Mevcut durum özeti (başlangıç noktası)

**Elimizde olan ve korunacaklar**
- `Company` + `CompanyOwnedModel` ile şirket izolasyonu çalışıyor. Sorgular şirkete göre filtreleniyor, başka şirketin kaydına FK bağlanamıyor. Bunun testleri var.
- Zeytin alımı: elek istasyonu, sıra no, cins × numara (11–17) bazlı kg ve fiyat, fiyat snapshot'ı, yağlık ayırma, komisyon, çiftçi borç/ödeme, önceki/yeni bakiye, WhatsApp fişi, yazdırma.
- Sıkım: `Customer.oil_process_status`, `oil_output_liters`, kg/litre oranı.
- Satış: tüccar (bireysel/kurumsal), zeytin ve yağ kalemleri, ödemeler, araç/şoför, sevkiyat (yükleme/yolda/ulaştı), stok girişleri.
- Excel rapor. (Electron masaüstü paketi 2026-10-26'da kaldırıldı; bkz. Karar 1.)

**Yeni yapıya engel olan noktalar**
- Ürün **zeytine sabit kodlanmış**: `size_11 … size_17`, `price_11 … price_17`, `olive_type` metin alanı. Kayısı, erik ve meysu bu yapıya sığmıyor.
- Çiftçi bağlantısı **isimle** kuruluyor: `CustomerSortingRecord.customer` bir CharField. Bakiye ve silme işlemleri isim eşleşmesine dayanıyor.
- Yetkiler 6 sabit boolean alandan ibaret (`can_manage_purchases/sales/users`). Rol kavramı yok, paket/modül kavramı yok.
- **Abonelik/süre** kavramı yok. Sadece `Company.is_active` var.
- Sıkım tarafında **makine, sıkım partisi, verim ve tank hareketi** yok. `StorageTank` ve `OliveBatch` modelleri var ama süreçlere bağlı değil.
- Stok bir **hareket defteri** olarak tutulmuyor. `InventoryEntry` manuel giriş; alım, satış ve sıkım stoğu otomatik etkilemiyor.
- Frontend tek dosya: `App.jsx` 7.576 satır. Modül eklemek pratikte imkânsız.

**meysu-takip'ten alınacaklar** (`/Users/dartanyan/Desktop/AnkaForge/jobs/web/meysu-takip`)
- `Mustahsil` + `MustahsilItem`: çiftçiden kg × fiyat alımı, verilen para, kalan.
- `Kantarci` + `Kantar`: kantar/toplayıcı bazlı alım; **dolu/boş kasa** sayısı, kg, fiyat, verilen para, açıklama.
- `Giden`: araç plakası, **müstahsil kg / fabrika kg / fire kg**, fiyat (fabrika kg üzerinden), gelen para, kalan.
- Tarih aralığı filtresi, borç durumu filtresi, kişi detay sayfası, arama, PDF hesap dökümü.
- Not: Bu projede şirket ayrımı, ürün türü ve araç/şoför ilişkisi yok. Mantığı alınacak, kodu alınmayacak.

---

## Kararlar (2026-10-26)

- [x] **Karar 1 — Dağıtım modeli:** İki sürüm olacak: web ve masaüstü. **Şimdilik sadece web + PostgreSQL.** Electron ve yerel SQLite kaldırıldı. Masaüstü (paket bazlı .exe) daha sonra ayrı bir faz olarak, aynı backend'e bağlanacak şekilde yapılacak.
- [x] **Karar 2 — Ortak çekirdek:** Cari, araç/şoför, raporlar ve kullanıcı yönetimi **her pakette** var. Paketlere göre değişen kısım:
  - Zeytin: alım, satış, lojistik
  - Zeytinyağı: sıkım, tank, yağ satışı
  - Meyve: kayısı, erik ve sonradan eklenecek meyveler
  - Meysu: kantar, müstahsil, fabrikaya giden
  - Full: hepsi
- [x] **Karar 3 — Süre bitimi:** Bitiş tarihinden sonra **10 gün ek süre** verilir. Bu sürede erişim devam eder, uyarı gösterilir. 10. günün sonunda şirketin tüm hesaplarına erişim engellenir. Veri silinmez; ödeme alınınca yeniden açılır.
- [x] **Karar 4 — Paket ekleme:** Yıl ortasında paket eklenebilir. Abonelik kalemleri paket bazında tutulur ve her birinin kendi başlangıç/bitiş tarihi olur.
  - Varsayım (onay bekliyor): sadece eklenen paketin süresi dolarsa o paketin modülleri 10 gün sonra kapanır, diğerleri çalışmaya devam eder. Hiç geçerli paket kalmazsa şirket tamamen dondurulur.
- [x] **Karar 5 — Veri taşıma yok.** Sazak'ın mevcut verisi taşınmayacak. Mevcut işleyiş ve iş kuralları yeni yapıya kod olarak aktarılacak. Faz 13 bu nedenle iptal edildi.

---

## Faz 0 — Temizlik ve güvenlik (yeni işe başlamadan)

- [x] `backend/db.sqlite3`, `db.sqlite3.before-reset-*`, tüm `__pycache__/`, `*.pyc` ve `.vite/` dosyalarını `.gitignore`'a ekle, `git rm --cached` ile repodan çıkar.
- [ ] Repo public ise geçmişi temizle (`git filter-repo`) ve `admin`/`kemalcekic` şifrelerini değiştir.
- [x] Electron'u tamamen kaldır: `frontend/electron/`, `frontend/build/`, `backend/desktop_server.py`, `requirements-desktop.txt`, `package.json` içindeki build ayarları, `window.electron` yazdırma köprüsü, `apiBaseUrl` parametresi.
- [x] `TIME_ZONE='Europe/Istanbul'`, `LANGUAGE_CODE='tr'`.
- [x] Veritabanı geçişi: PostgreSQL (`DATABASE_URL` + `dj-database-url` + `psycopg`). SQLite tamamen kaldırıldı; yerel geliştirme için `docker-compose.yml` eklendi.
- [ ] Python 3.12+ ve PostgreSQL ortamında mevcut testleri çalıştır, yeşil olduğunu doğrula. Bu, refactor öncesi güvenlik ağı.
- [ ] `console.log` artıklarını temizle (ör. `App.jsx:1003`).
- [ ] Basit CI kur (GitHub Actions): `manage.py test`, `makemigrations --check`, `npm run lint`, `npm run build`.

---

## Faz 1 — Platform çekirdeği: şirket, paket, abonelik ✅ (2026-10-26)

Yeni Django app: `backend/subscriptions/`. 59 test geçiyor (35 mevcut + 24 yeni), SQLite üzerinde çalıştırıldı; PostgreSQL üzerinde henüz çalıştırılmadı.

- [x] **`Module`**: `users`, `parties`, `logistics`, `reports` çekirdek modüller (her pakette açık, Karar 2); `olive`, `olive_oil`, `fruit`, `meysu` ürün modülleri. Seed: `0002_seed_modules_and_packages`.
- [x] **`Package`**: Zeytin, Zeytinyağı, Meyve, Meysu, Full; liste fiyatı (admin'den girilecek, şu an 0), süre 365 gün, paket bazlı ek süre (`grace_days`; boşsa varsayılan 10 gün).
- [x] **Demo paketi**: 10 gün, tüm modüller açık, **ek süre yok** (11. gün kapanır). Kurulum ekranında seçilirse ücret 0 ve ödeme "Ücretsiz / deneme" olur. Mevcut şirketlere otomatik abonelik verilmiyor (canlıda şirket yok).
- [x] **`Company`** genişletmesi: vergi no/daire, yetkili, telefon, e-posta, adres, not. `is_active=False` → elle dondurma.
  - [ ] Logo (fiş ve PDF için): medya depolama kararı ile birlikte (Faz 14).
- [x] **`Subscription`** (yenileme takip modeli): şirket, paket, başlangıç, bitiş, ücret, ödeme durumu/tarihi/yöntemi, dekont no, ankaforge sipariş no, yenilenen kayıt, iptal, not, kaydeden admin. Her yenileme yeni kayıt; silme kapalı, iptal var.
  - Durum veritabanında tutulmuyor, tarihten anlık hesaplanıyor: `upcoming` / `active` / `grace` / `expired` / `cancelled`. Böylece cron çalışmasa bile erişim doğru günde kapanır.
- [x] Erişim servisi `subscriptions/access.py` → `get_company_access(company)`: durum (`active` / `grace` / `expired` / `frozen`), açık modüller, bitiş, ek süre bitişi, kalan gün, paket listesi.
- [x] **Ek süre ve dondurma (Karar 3 ve 4):**
  - [x] Bitişten sonra paketin ek süresi (varsayılan `SUBSCRIPTION_GRACE_DAYS` = 10, demoda 0) boyunca erişim açık; 11. gün giriş ve tüm API 403 (`code: company_expired`).
  - [x] Paket bazlı: sadece süresi dolan paketin modülleri kapanır (`code: module_not_in_package`); hiç geçerli paket kalmazsa şirket tamamen kapanır.
  - [x] Elle dondurulan şirket: `code: company_frozen`.
  - [x] Veriye dokunulmuyor; yenileme veya aktifleştirme ile her şey yerinde açılıyor (testli).
  - [x] Platform süper kullanıcısı bu kontrollerden etkilenmiyor.
- [x] Erken yenileme veya ek sürede yenileme: yeni dönem eski bitişin ertesi günü başlar (boşluk/çakışma yok). Tamamen dolmuşsa bugünden başlar.
- [x] **`manage.py check_subscriptions`**: 30 gün içinde bitecek, ek sürede olan ve bugün kapanan abonelikleri telefonla listeler. Kayıt değiştirmez.
  - [ ] Sunucuda günlük cron olarak kurulması (Faz 14). E-posta bildirimi opsiyonel.
- [x] **Django admin:**
  - [x] Şirket listesi: erişim durumu rozeti, paketler, son bitiş tarihi; şirket formunda abonelikler inline.
  - [x] Abonelik listesi: renkli durum, kalan gün / ek süre, filtreler (aktif / 30 gün içinde bitecek / ek süre / dolmuş / başlamamış / iptal, ödeme durumu, paket), arama.
  - [x] Aksiyonlar: **"Bir dönem yenile"** (ödeme bilgisi soran ara ekranla), **"Ödendi işaretle"**, **"İptal et"**, şirket için **"Dondur"** ve **"Aktifleştir"**.
  - [x] **"Yeni şirket kur"** ekranı (Şirketler listesinin sağ üstünde): şirket + paket + genel admin tek adımda. Geçici şifre üretilir ve WhatsApp/e-posta için hazır metin verilir. Giriş adresi `FRONTEND_URL` ayarından alınır.
- [x] API: `POST /api/login/` ve yeni `GET /api/me/` yanıtında `access` nesnesi (`state`, `modules`, `ends_on`, `grace_ends_on`, `days_left`, `packages`, `message`).
- [x] Frontend:
  - [x] Açılışta `/api/me/` ile paket durumu tazelenir.
  - [x] Erişim kapanırsa (`company_*` 403 veya 401) oturum kapanır, giriş ekranında sebep gösterilir.
  - [x] Uyarı bandı: ek sürede tüm kullanıcılara; bitişe 30 gün kala ve tek paket ek süredeyken genel admine.
  - [x] Mevcut alış/satış ekranları `olive` modülüne bağlandı.
  - [ ] Diğer paketlerin menüleri ilgili fazlarda eklenecek. Şu an sadece Meyve veya Meysu paketi olan bir şirket boş bir ekran görür.
- [ ] Not (Faz 6): `SalesOilItem` / `SalesOilPrice` şimdilik `olive` modülünde, `StorageTank` ise `olive_oil` modülünde. Sıkım modülü yazılırken yağ satışı `olive_oil` modülüne taşınacak.

---

## Faz 2 — Roller ve yetkiler

- [ ] Sabit boolean alanların yerine **rol** sistemi:
  - **`Role`** (şirkete ait): ad, açıklama, `is_company_admin`.
  - **`RolePermission`**: rol × modül × eylem (`view`, `create`, `edit`, `delete`, `approve`, `export`).
  - **`AppUserProfile`**: şirket, `roles` (M2M), telefon, aktif mi.
- [ ] Her yeni şirkete hazır **rol şablonları** yüklensin (genel admin düzenleyebilir):
  - Genel Admin: her yer, paketle sınırlı.
  - Satış Admini: satış, tüccar, sevkiyat, araç/şoför.
  - Elek Görevlisi: kendi istasyonunda alım kaydı oluşturur ve görür. Fiyat düzenleyemez, silemez.
  - Yağ Sıkım Elemanı: sıkım partileri, makine, tank.
  - Muhasebe: tüm cari hesaplar, ödemeler, raporlar. Operasyonel kayıt silemez.
  - Kantar Görevlisi: meysu ve meyve kantar girişi.
- [ ] **Kayıt kapsamı (opsiyonel ama değerli):** kullanıcıyı belirli elek istasyonu, kantar veya makineye bağlama. Elek görevlisi sadece kendi elek istasyonunu görsün.
- [ ] **Etkin yetki** = şirketin aktif modülleri ∩ kullanıcının rol yetkileri. Tek bir `HasModulePermission` sınıfı olsun; her ViewSet `module = '...'` tanımlasın.
- [ ] Genel admin (`is_company_admin`): kendi şirketinde her yere girer, kullanıcı ve rol yönetir. Başka şirketi asla göremez.
- [ ] Platform süper kullanıcısı (siz): sadece Django admin'den çalışsın. API'de şirket profili yoksa her şeyi görme davranışı kaldırılsın veya "şirket seçerek görüntüleme" ile sınırlansın.
- [ ] Kullanıcı yönetimi ekranı: rol atama, şifre sıfırlama, pasifleştirme.
- [ ] **İşlem kaydı (audit log):** kim, ne zaman, hangi kaydı oluşturdu/değiştirdi/sildi. Muhasebe anlaşmazlıklarında gerekli; `django-simple-history` veya basit bir `AuditLog` modeli yeterli.
- [ ] Testler: her rol şablonu için izin matrisi testi.

---

## Faz 3 — Ürün kataloğu (zeytine sabit yapıyı kaldırmak)

Ortak app: `catalog`.

- [ ] **`ProductCategory`**: zeytin, zeytinyağı, kayısı, erik, meysu… Kategori hangi modüle ait bilgisini tutsun.
- [ ] **`ProductVariety`** (tür/cins): şirkete ait. Örn. zeytin → Gemlik, Domat; kayısı → Hacıhaliloğlu; erik → Can, Papaz.
- [ ] **`ProductGrade`** (boy/numara/kalite): kategoriye veya türe bağlı, sıralı. Zeytin 11–17; erik iri/orta/küçük; meysu tek boy.
- [ ] **Birim:** kg / litre / kasa. Zeytinyağı litre ve kg arasında yoğunluk dönüşümü.
- [ ] **`PriceList`** + **`PriceListItem`**: tarih aralıklı fiyat; alış ve satış ayrı; tür × boy bazında. Mevcut `OlivePrice`, `SalesPrice` ve `SalesOilPrice` modellerinin yerini alır.
- [ ] Fiyat snapshot mantığı korunacak: kayıt anındaki fiyat satıra yazılır, sonradan fiyat değişse de eski kayıt değişmez.
- [ ] Genel admin kendi tür ve boylarını yönetebilsin (ekran).

---

## Faz 4 — Cari hesaplar (çiftçi, tüccar, personel)

Ortak app: `parties`.

- [ ] **`Party`**: tip (`farmer` / `merchant` / `factory` / `collector`), bireysel/kurumsal, ad, telefon, TC/VKN (opsiyonel), adres, IBAN, not, aktif mi.
  - Mevcut `Customer`, `MerchantParty` ve meysu'daki `Mustahsil`/`Kantarci` modellerinin yerini alır.
  - Aynı kişi hem çiftçi hem tüccar olabilir.
- [ ] Tüm alım ve satış kayıtları cariye **FK ile** bağlansın (isimle değil).
- [ ] **`LedgerEntry`** (cari hareket defteri): cari, tarih, kaynak (alım / satış / ödeme / tahsilat / sıkım ücreti / yağ teslimi / komisyon), borç, alacak, açıklama, kaynak kayıt referansı.
  - Bakiye bu defterden hesaplansın. Mevcut `previous_balance` döngüsü (her kayıtta tüm geçmişi yeniden sorgulayan yapı) yerine bu kullanılacak.
- [ ] Ödeme ve tahsilat: nakit / havale / çek / mahsup; tek ödeme birden fazla kayda dağıtılabilsin.
- [ ] Cari ekstresi: tarih aralığı, PDF/Excel, WhatsApp ile gönder.
- [ ] Sorumlu personel komisyonları (`ResponsiblePerson`) da bu deftere bağlansın.
- [ ] "Çiftçiden alacaklı mı, borçlu mu" bilgisi tek bakiye alanından okunabilsin.

---

## Faz 5 — Alım modülü (ürünlerden bağımsız)

Ortak app: `purchasing`. Zeytin, kayısı, erik ve meysu aynı akışı kullanacak.

- [ ] **`CollectionPoint`**: elek istasyonu / kantar / alım noktası. Mevcut `SieveStation` ve meysu'daki `Kantarci` bunun altında birleşsin. Komisyon kuralları ve sorumlu personel korunacak.
- [ ] **`PurchaseReceipt`** (alım fişi):
  - Şirket, alım noktası, tarih, günlük sıra no (istasyon bazında; mevcut mantık korunacak), cari (çiftçi), sorumlu personel, kategori.
  - Varış yeri: **kendi fabrikasına / ticari stok / fason sıkım**.
  - Ödeme tutarları, WhatsApp durumu.
- [ ] **`PurchaseLine`**: tür, boy, brüt kg, dara, net kg, birim fiyat snapshot, tutar. Ayrıca yağlığa ayrıldı mı bilgisi (mevcut `oil_release` mantığı satır bazında).
- [ ] Meysu ve meyve kantarı için ek alanlar: **dolu kasa / boş kasa** sayısı (meysu-takip `Kantar`), açıklama.
- [ ] Alım fişi kaydedilince:
  - Cariye alacak hareketi yazılsın.
  - Yağlığa ayrılan kısım sıkım kuyruğuna düşsün.
  - Kalan kısım stoğa giriş olarak yazılsın.
- [ ] Mevcut fiş/WhatsApp/yazdırma şablonları ürün bağımsız hale getirilsin (tür × boy tablosu dinamik olsun).
- [ ] Komisyon hesabı (`total_weight` / `net_weight` / `oil_weight` / `sales_amount`) aynen korunsun ve testleri taşınsın.

---

## Faz 6 — Yağ sıkım modülü (Zeytinyağı paketi)

App: `pressing`.

- [ ] **`PressMachine`** (makine/hat): ad, kapasite, aktif mi.
- [ ] **`PressingBatch`** (sıkım partisi):
  - Tarih/saat başlangıç–bitiş, makine, operatör.
  - Tip: **fason** (çiftçinin zeytini, yağı çiftçiye) / **kendi** (şirketin aldığı zeytin).
  - Giren zeytin kg, çıkan yağ litre/kg, asit vb. kalite notları, pirina.
- [ ] Partiye bağlanacak alım satırları veya çiftçi seçilebilsin. Bir partide birden fazla çiftçi olabilir (paylaştırma oranı ile).
- [ ] **Fason hesap:**
  - Çiftçiye teslim edilen yağ.
  - Şirkete kalan yağ: ücret karşılığı yağ veya yüzde.
  - Sıkım ücreti → cari deftere.
  - Bunlar mevcut `oil_output_liters`, `oil_process_status` ve kg/litre alanlarının yerini alır.
- [ ] **Verim raporu:** makine bazında kg zeytin / litre yağ, randıman %, günlük/sezonluk üretim. Bu, "hangi makine daha verimli" sorusunun cevabı.
- [ ] **`Tank`** + **`TankMovement`**: üretimden giriş, satış/teslim çıkışı, tanklar arası transfer. Doluluk hareketlerden hesaplansın; `current_liters` elle tutulmasın.
- [ ] Sıkım kuyruğu ekranı: bekleyen, sıkımda, tamamlanan (mevcut durum akışı korunarak).

---

## Faz 7 — Stok defteri

App: `inventory`.

- [ ] **`StockMovement`**: kategori, tür, boy, depo/tank, miktar (+/−), birim, kaynak (alım / satış / sıkım girdisi / sıkım çıktısı / fire / sayım düzeltmesi / manuel), kaynak kaydı referansı.
- [ ] Stok bakiyesi = hareketlerin toplamı. Mevcut `InventoryEntry` "manuel düzeltme" hareketine dönüşsün.
- [ ] **`Warehouse`** (depo / soğuk hava / tank grubu), opsiyonel.
- [ ] Satış kaydı stoktan düşsün; stok yetersizse uyarı versin (engelleme ayarlanabilir).
- [ ] Fire: meysu'daki `mut_kg − fabrika_kg` mantığı genel "teslimde fire" olarak satış ve sevkiyata taşınsın.

---

## Faz 8 — Satış ve lojistik

Apps: `sales`, `logistics`.

- [ ] **`SalesOrder`**: tüccar (Party), tarih, satış no (şirket bazında), kalemler, ödemeler, WhatsApp. Mevcut `SalesRecord` mantığı korunacak.
- [ ] **`SalesLine`**: kategori / tür / boy / miktar / birim / fiyat snapshot. Zeytin, yağ, kayısı, erik ve meysu aynı tabloda; `SalesItem` ve `SalesOilItem` birleşir.
- [ ] **Sevkiyat:**
  - [ ] `Shipment`: araç, şoför, çıkış yeri, teslim adresi, durum (yükleniyor / yolda / ulaştı / teslim edildi), zaman damgaları.
  - [ ] Bir satışın birden fazla sevkiyatı, bir sevkiyatta birden fazla satış olabilsin.
  - [ ] `ShipmentLine`: yüklenen miktar, teslim edilen miktar, **fire**. Fabrika/tüccar kantarında tartılan miktar üzerinden faturalama seçeneği (meysu `Giden` mantığı).
  - [ ] **"Nerede" takibi:** durum geçmişi (`ShipmentStatusLog`), en azından elle konum/not. Canlı GPS ayrı bir faz olarak düşünülebilir.
- [ ] **Araç ve şoför:** mevcut yapı korunsun. Şoförün hangi seferleri yaptığı ve hangi aracın hangi yükü taşıdığı raporlanabilsin.
- [ ] Sevkiyat irsaliyesi yazdırma/PDF.

---

## Faz 9 — Ürün modülleri (paketlerin içi)

Çekirdek (Faz 3–8) hazır olunca her paket büyük ölçüde **yapılandırma** olur:

- [ ] **Zeytin paketi:** elek bazlı alım, 11–17 numara, yağlık ayırma, tüccara satış, sevkiyat. Mevcut özelliklerin tamamı yeni yapıda çalışmalı (regresyon listesi çıkarılacak).
- [ ] **Zeytinyağı paketi:** sıkım, makine, tank, fason, yağ satışı.
- [ ] **Meyve paketi:** kayısı ve erik türleri ile boyları (seed), kasa bazlı kantar, aynı alım/satış akışı. Kurutmalık/sofralık gibi kullanım ayrımı gerekiyorsa ek alan.
- [ ] **Meysu paketi:** meysu-takip'teki müstahsil, kantar ve giden akışları; dolu/boş kasa; fabrika kg ile fire hesabı; PDF hesap dökümü.
- [ ] **Full paket:** tüm modüller.
- [ ] Her paket için seed komutu: `manage.py seed_package <company> <package>` kategori, tür, boy ve rol şablonlarını yüklesin.

---

## Faz 10 — Raporlar

- [ ] Alım: elek/kantar × tür × boy × tarih → kg, tutar, çiftçiye ödenen, kalan.
- [ ] Sıkım: makine bazında giren kg, çıkan yağ, randıman; çiftçiye verilen ve fabrikaya kalan.
- [ ] Cari: çiftçi borç/alacak listesi, yaşlandırma, ekstre.
- [ ] Satış: tüccar × ürün × dönem; tahsil edilen ve kalan.
- [ ] Lojistik: araç/şoför bazında seferler, taşınan miktar, fire.
- [ ] Stok: anlık stok, tank doluluk, hareket dökümü.
- [ ] Sezon özeti panosu (genel admin).
- [ ] Tüm raporlarda tarih aralığı, Excel ve PDF çıktısı. Mevcut `excelReports.js` genelleştirilecek.
- [ ] Ağır raporlar için backend'de toplama (aggregate) endpoint'leri. Şu anda tüm listeler frontend'e çekilip orada hesaplanıyor.

---

## Faz 11 — Backend mimarisi

- [ ] Veri taşıma olmadığı için yeni app'ler **temiz migration'larla** başlasın; eski `core` migration zinciri (0001–0031) taşınmak zorunda değil.
- [ ] Tek `core` app'i modüllere böl: `platform`, `catalog`, `parties`, `purchasing`, `pressing`, `inventory`, `sales`, `logistics`, `reports`.
- [ ] Hesaplamalar `services.py` katmanına taşınsın. Kayıt, defter ve stok yazımı tek transaction içinde yapılsın.
- [ ] Toplamlar kayıt anında hesaplanıp saklansın. Property içinde N+1 sorgu atan hesapların (`total_commission`, `previous_balance`) yerini alsın.
- [ ] Liste endpoint'lerine sayfalama, filtreleme (`django-filter`) ve arama eklensin.
- [ ] API sürümleme (`/api/v2/`), çünkü eski frontend ile geçişte iki sürüm bir süre birlikte yaşayabilir.
- [ ] Login rate limit, token süresi ve logout'ta token silme.
- [ ] Silme yerine soft-delete (pasifleştirme), özellikle cari ve fişlerde.

---

## Faz 12 — Frontend mimarisi

- [ ] `App.jsx` (7.576 satır) parçalansın:
  - React Router ile sayfa bazlı yapı.
  - `src/modules/<modül>/` altında sayfalar, bileşenler ve API.
- [ ] Oturum, şirket, aktif modüller ve yetkiler için tek bir `AuthContext`. Menü ve sayfalar `can(module, action)` ile korunsun.
- [ ] Veri katmanı: TanStack Query (cache, yükleniyor/hata durumları).
- [ ] Ürün bağımsız ortak bileşenler: tür × boy giriş tablosu, cari seçici, fiş önizleme, tarih aralığı filtresi, Excel/PDF butonu.
- [ ] Sıralama: mevcut ekranları yeni yapıya **birebir** taşı, sonra genelleştir.
- [ ] Mobil kullanım: elek ve kantar görevlisi büyük ihtimalle telefondan girecek. Bu ekranlar mobil öncelikli tasarlansın.
- [ ] Opsiyonel: TypeScript'e kademeli geçiş.

---

## ~~Faz 13 — Veri taşıma~~ (İPTAL — Karar 5: veri taşınmayacak, aşağıdakiler yapılmayacak)

- [ ] Eski şemadan yeni şemaya migration/script:
  - `Customer` / `MerchantParty` → `Party`
  - `CustomerSortingRecord` + `Item` → `PurchaseReceipt` + `PurchaseLine` (`size_11..17` satırlara açılır)
  - Ödemeler → `LedgerEntry`
  - `SalesRecord` → `SalesOrder`
  - `Shipment` → yeni sevkiyat yapısı
  - Fiyatlar → `PriceList`
- [ ] İsimle bağlı kayıtların (`customer` CharField) `Party` ile eşleştirilmesi; eşleşmeyenlerin raporu çıkarılsın.
- [ ] Doğrulama: taşıma öncesi ve sonrası çiftçi bakiyeleri, toplam kg ve tutarlar birebir aynı olmalı. Bunun için otomatik karşılaştırma script'i yazılsın.
- [ ] meysu-takip verileri (Sazak) de Meysu modülüne aktarılsın.

---

## Faz 14 — Yayın ve operasyon

- [ ] Sunucu: Django + gunicorn + PostgreSQL. Render/Railway/VPS seçimi yapılsın. `render.yaml` veya Docker dosyası yazılsın.
- [ ] Otomatik günlük veritabanı yedeği ve geri yükleme provası.
- [ ] Hata takibi (Sentry) ve loglama.
- [ ] `check_subscriptions` için cron.
- [ ] Alan adı, örn. `app.ankaforge.com`, ve HTTPS.
- [ ] (Sonraki aşama) Masaüstü sürüm: paket bazlı .exe, aynı web backend'ine bağlanır; sessiz fiş yazdırma, kod imzalama, otomatik güncelleme. Eski Electron kodu git geçmişinde duruyor (`frontend/electron/main.cjs`).
- [ ] KVKK aydınlatma metni, kullanım sözleşmesi (paket satışı için gerekli), gizlilik politikası.
- [ ] Kurulum dokümanı: "Yeni şirket nasıl açılır, paket nasıl yenilenir" (sizin için iç kullanım), ayrıca genel admin için kısa kullanım kılavuzu.

---

## Önerilen sıra

1. Faz 0 → kararlar (1–5)
2. Faz 1 + 2 (platform, abonelik, roller). Mevcut zeytin ekranlarıyla birlikte bile yayınlanabilir; Sazak ve İzorya'yı ayrı şirket olarak açmak hemen mümkün olur.
3. Faz 3 + 4 + 11 (katalog, cari defter, backend bölme)
4. Faz 5 + 7 + 8 (alım, stok, satış/lojistik)
5. Faz 6 (sıkım)
6. Faz 9 (meyve ve meysu paketleri) + Faz 10 (raporlar)
7. Faz 12 frontend işi Faz 3'ten itibaren paralel yürür.
8. Faz 14
