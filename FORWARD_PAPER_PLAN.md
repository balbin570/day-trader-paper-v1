# 10.000 USD forward-paper portföy — güvenli uygulama planı

Bu belge uygulama planıdır; portföy motoru henüz devrede değildir. Gerçek emir,
broker bağlantısı ve canlı işlem modu eklenmeyecek. Eski sonuçlar korunacak.

## Şimdi düzeltilenler

- XNYS takvimi: New York yaz/kış saati, tatiller, erken ve bilinen özel kapanışlar.
  Takvim paketi sabit sürümlüdür; yeni olağanüstü kapanışlarda güncellenmesi gerekir.
- Pozitif ve sonlu OHLC/hacim, eşit uzunluklu Yahoo dizileri, tamamlanmış ve
  sıralanmış mumlar; çakışan aynı zamanlı mumlar ve 21 mumluk penceredeki boşluklar reddedilir.
- Güncel seans, en çok 10 dakika veri yaşı; ilk 105 dakikada strateji ısınması.
- Aynı strateji/sembol/mum sinyali tekrar sayılmaz. Ardışık farklı mumlar ayrı
  gözlemdir; bunlar bağımsız istatistik örnekleri kabul edilmemelidir.
- `results/v2/` ayrı veri alanıdır. Eski `results/latest.json` ve `results/history/`
  değiştirilmez. Eski TSLA sonuçları yeniden hesaplanmaz, v2 ile birleştirilmez.
- 30/60/120 dakika değerlendirmesi gerçek gözlem zamanından başlar; hedef veya
  en fazla 5 dakika sonraki tamamlanmış mum kapanışı kullanılır. Gelecek/eksik,
  ertesi seans ve erken kapanış sonrası fiyat kullanılmaz. Eksik ölçüm boş kalır.
- Getiriler sinyal fiyatı değişimidir; gerçekleşmiş işlem kârı değildir. Brüt ve
  varsayımsal maliyet sonrası getiri ayrıdır. Her yön için 5 baz puan ücret +
  5 baz puan kayma, toplam 20 baz puan (%0,20) varsayılmıştır. Yahoo işlem verisi değildir.
- 15 dakikalık Actions isteği kesin zaman garantisi vermez. Geç gelen çalışma
  geçmişten sahte giriş açamaz. Hata tanıları da atomik JSON, artifact ve commit ile korunur.

## 1. Sürümü ve başlangıcı sabitle

Yeni `paper_portfolio_v1` deney kimliği ve açık UTC başlangıç zamanı kaydet.
Başlangıç nakdi 10.000 USD; eski sinyallerden pozisyon açma. Ayrı portföy durumu,
işlem günlüğü ve gerçekleşme varsayımları tut. Mevcut breakout baz strateji kalır.
Trend (ör. 20/50 ortalama), volatilite (ATR), göreli hacim ve SPY/QQQ piyasa yönü
filtreleri ayrı strateji kimlikleriyle, yalnız o anda bilinen verilerle ölçülür.
Her stratejinin aynı sermayeli ayrı defteri olur; sonuçlar sonradan seçilip birleştirilmez.

## 2. Sermaye ve risk

Sadece long, tam hisse, kaldıraç ve açığa satış yok. En çok 5 açık pozisyon ve
sembol başına tek pozisyon. Pozisyon başına portföy özkaynağının %0,5'i risk
(başlangıçta 50 USD), toplam açık başlangıç riski en çok %2,5; pozisyon nominali
en çok özkaynağın %20'si. Miktar, stop mesafesi ve tahmini tüm maliyetlerle aşağı
yuvarlanır, nakit sınırını aşamaz. Stop garantili zarar limiti değildir; boşlukta
zarar bütçeyi aşabilir. Günlük özkaynak kaybı %2 olursa yeni girişleri durdur,
mevcut çıkışları sürdür. Aynı anda gelen adayları sabit sembol sırası ile işle.

## 3. Giriş ve çıkış

Sinyal yalnız aday oluşturur. Gözlem kaydedildikten sonraki ilk taze çalışma
anında görülen, sinyal gözleminden sonra başlamış ve tamamen kapanmış mumun
kapanışı + 5 baz puan kayma varsayımsal giriş referansıdır. Mum kapanışı
çalışma anından en çok 5 dakika eski olmalı. Aday 20 dakikada gerçekleşmezse
iptal edilir. Eski mum açılışında işlem yapılmış sayılmaz. Bu, piyasa dolumu
garantisi olmayan açıkça etiketli bir kapanış fiyatı modelidir.

Başlangıç stopu girişin %1 altında, hedef %2 üstünde; stop genişletilmez.
Yalnız girişten sonra başlayan mumlar çıkış için kullanılabilir. Bir mumda hem
stop hem hedef görülürse stop önce kabul edilir. Aşağı boşlukta stop fiyatı
yerine daha kötü açılış, ardından olumsuz kayma kullanılır. Hedefte iyimser
fiyat iyileşmesi verilmez. En geç 120 dakika veya seans kapanışı ile süre çıkışı;
veri yoksa gerçekleşme uydurma, pozisyonu `EXIT_PENDING_DATA` olarak raporla
ve yeni girişleri durdur. Gecikmiş veriyle kapanış gerekiyorsa işlem modelinin
gecikmesini ayrıca göster; garantili seans içi kapanış iddiasında bulunma.
OHLC ve gözlem zamanı saklanmadan bu motor etkinleştirilemez.

## 4. Kalıcı kayıt ve tekrar güvenliği

Sinyal kimliği, portföy kimliği ve benzersiz olay kimliği ile append-only işlem
günlüğü; bu günlükten türeyen nakit/pozisyon/özkaynak durumu. Tek yazıcı,
atomik dosya değişimi ve Actions concurrency. Aynı run tekrarında giriş,
çıkış ve ücret iki kez yazılmamalı. Kalıcı kayıt başarısızsa bildirim veya yeni
işlem ilerletilmez. Başarısız push için artifact kurtarma prosedürü ve başlangıçta
bütünlük kontrolü gerekir. Açık pozisyon fiyatı bayatsa son fiyatın yaşı gösterilir;
bilinmeyen güncel özkaynak kesin değer olarak sunulmaz.

## 5. Rapor ve isteğe bağlı Telegram

New York işlem gününe göre günlük Türkçe rapor: taranan 12 sembol, veri kapsamı,
yeni/tekrar sinyaller, açık pozisyonlar, kapanan işlemler, nakit, brüt/net
getiri, ücret/kayma, gerçekleşmiş/gerçekleşmemiş kâr ve hatalar. Raporlar strateji
ve sürüm bazında ayrılır. Telegram token/chat bilgileri yalnız GitHub Secrets'tan
okunur; eksikse rapor dosyası yine üretilir. Bildirim ayrı ve isteğe bağlıdır,
portföy hatalarını gizlemez; token veya ham HTTP hata adresi loglanmaz.

## 6. Etkinleştirme kapıları

Önce miktar/nakit/risk, boşlukta stop, aynı mumda stop+hedef, eksik veri,
seans sonu, tekrar run, yazma/push hatası ve eski veri testlerini geçir.
Sonra ayrı paper deneyini başlat; ilk canlı veri çalışmasında günlük ile durumu
uzlaştır. Eksik/yinelenmiş gözlem oranını raporla. En az 20 seans/100 benzersiz
sinyal yalnız ilk betimleyici raporlama eşiğidir, kârlılık kanıtı değildir.
Seans bazında bağımlılık, örneklem büyüklüğü ve belirsizlik mutlaka gösterilir.
