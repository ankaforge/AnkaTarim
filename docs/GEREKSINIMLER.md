# Anka Tarım — Yeni Yapı Gereksinimleri

> Kaynak: proje sahibinin 2026-10-26 tarihli talebi (orijinal metin aşağıda olduğu gibi korunmuştur).

---

Bu sistemin amacı tarım ürünlerinin alım satım süreçlerini kağıttan dijitale geçmek ve verimlilik sağlamak.

bunu değiştreceğiz biraz. mevcut özellikleri koruyacağız fakat daha modüler hale getireceğiz.

Bunu birden fazla şirket kullanabilir olacak.
Bir şirketin değişik görevlerde tanımladığı kullanıcılarda sınırlı yetkilerle bunu kullanacak.
örn şirket sazak zeytin, sazak zeytinin genel admini ayrı olur satış admini ayrı yağ sıkım elemanı ayrı elek görevlisi ayrı anladın mı.

başka bir şirket İzorya zeytinyağı bunun da genel admini ayrı olur satış admini ayrı yağ sıkım elemanı ayrı elek görevlisi ayrı anladın mı. nuhasebe vs ayrı ayrı yani


çok şirketli ve şirketlerin de çok kullanıcılı olduğu ve bir şirketin genel adminnin her yere girebildiği bir sistem düşün.

Bir de zeytin paketi + zeytinyağı paketi + meyve paketi + meysu paketi gibi paketler yapacağız. bir de hepsini kapsayan full paket oalcak. bu paketler ücretli olacak tabi ve ankaforge.com sitesi üzerinden satın alınacak. ama merak etme otomatik bir düzen değil.
ankaforgeden alınan paket neyse örn zeytin biz django admin üzerinden şirket kaydnı ve genel admin atamasını yapacağız. sonrasında genel admin giriş bilgilerini kendimiz whatsapp e-posta yoluyala manuel ileteceğiz. genel adminde varsa çalışanlarını ekler olur biter.
Dikkat! bir paketin kullanım süresi 1 yıldır. Bir yıl sonunda paket yenilemesi yapılmazsa şirkete ait tüm hesaplar dondurulur. ödeme alındıktan sonra tekrar aktife alınır verileri silinmez.

Bunun için django admim tarafında da bir yenileme takip modeli oluşturmalıyız.



Günün sonunda elimizdeki sistem şunu yapalimeli
örn sazak tarım zeytin alıyor zeytini başka tüccarlara satıyor kendi yağ fabrikasına zeytin alıyor ya da zeytin aldığı müşterinin zeytin yağını sıkıyor.

Hangi elekten hangi zeytinden ne kadar alınmış çiftçiye ne verilmiş, ne kadar zeytinyağı üretilmiş hangi makine daha verimli çalışmış da hangi makineden ne kadar zeytin yağı üretilmiş çiftçiye ne verilmiş fabirkaya ne kalmış, çiftçiden alacaklı mı borcu mu var, hangi zeytin hangi araçla hangi tüccara satılmış nerdeymiş bu hangi araç hangi şoför bunu taşımış bilecek.
yine sazak tarım kayısı ve erik alıyor hangi tür kayısında ne kadar alınmış çiftçiye ne verilmiş ne kalmış tüccara yine aynı zeytinde olduğıu gibi satış işlemleri ne olmuş?
erik alıyorlar erik hangi tür hangi boy yine aynı alımsatım süreçleri
meysu almış o da benzer.
hatta bak referans olabilir sana /Users/dartanyan/Desktop/AnkaForge/jobs/web/meysu-takip de sazak için geliştirdiğim meysu takip sistemi vardı inceleyebilirsin
