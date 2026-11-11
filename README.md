# US day trader — paper only

12 ABD enstrümanında 5 dakikalık breakout gözlemi. Broker bağlantısı veya gerçek emir yoktur.

Python 3.12: `pip install -r requirements.txt`, ardından `python -m unittest discover -v`.
`python scanner.py` tarar, `python evaluate_signals.py` 30/60/120 dakika ölçümlerini günceller.
Yeni çıktılar `results/v2/latest.json`, `results/v2/history/` ve değerlendirme hata durumudur.
Eski sonuçlar korunmuştur; v2 sonuçlarıyla karşılaştırırken yöntem farkları dikkate alınmalıdır.

GitHub Actions kod değişikliklerinde test, main değişikliklerinde ayrıca gerçek veri taraması;
zamanlama ve elle çalıştırmada tarama/değerlendirme yapar. Tarama başarısız olsa da
eldeki hata çıktıları kaydedilir. Ücretsiz Actions zamanlaması gecikebilir.

[10.000 USD sanal portföy uygulama planı](FORWARD_PAPER_PLAN.md)
