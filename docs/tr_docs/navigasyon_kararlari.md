# Navigasyon Karar Algoritması

## Giriş

AutoSo'nun, konuşmacının ne söylediğini yüksek doğrulukla tespit etmesi denklemin sadece bir yarısıdır. Diğer yarısı ise bu bilgiye dayanarak doğru eylemi gerçekleştirmektir: **Slaytı ilerlet (`forward`) mi, yoksa mevcut slaytta kal (`stay`) mi?**

Bu karar, `app.py` dosyasındaki `RealtimeNavigator` sınıfının `_determine_navigation_action` metodu içinde yer alan karmaşık ama son derece etkili bir mantıkla verilir. Bu mantık, sadece mevcut eşleşmeye değil, aynı zamanda sunumun genel bağlamına ve gelecekteki olası adımlara da bakar.

## Karar Verme Mekanizması

Karar algoritması, Python'un `match` ifadesini kullanarak üç temel durumu ve bu durumların alt koşullarını değerlendirir. Her karar, aşağıdaki değişkenlerin durumuna göre verilir:

-   `is_current_source`: Eşleşen chunk'ın kaynağı, şu anda beklenen transkript mi?
-   `early_forward`: Mevcut transkriptin `early_forward` bayrağı `true` mu?
-   `is_next_source_different`: Bir sonraki chunk, farklı bir transkriptten mi geliyor? (Bu, mevcut transkriptin sonuna gelindiğini gösterir.)
-   `expected_idx`: Eşleşen chunk'ın ait olduğu transkriptin indeksi.

### Durum 1: `Stay` (Mevcut Slaytta Kal)

Bu, sistemin en güvenli ve varsayılan eylemidir. Aşağıdaki senaryolarda `stay` kararı verilir:

-   **Senaryo A: Standart Akış**
    -   Eşleşen chunk, mevcut transkripte aittir.
    -   Konuşmacı, slaydın ortalarında bir yerden bahsetmektedir (`is_next_source_different` False'dur).
    -   `early_forward` bayrağı `false`'tur veya koşulları tetiklenmemiştir.
    -   **Sonuç:** Sistem, konuşmacının mevcut slayt hakkında konuşmaya devam ettiğini anlar ve hiçbir şey yapmaz.

-   **Senaryo B: Geriye Dönük Eşleşme**
    -   Konuşmacı tereddüt edip bir önceki cümleden bir kelimeyi tekrar ettiğinde, sistem yanlışlıkla geçmiş bir transkripte ait bir chunk ile eşleşebilir.
    -   Kodda `current_idx < expected_idx` kontrolü bu durumu yakalar. Eğer eşleşme geçmiş bir indeksten geliyorsa (`expected_idx` mevcut indeksten küçükse), sistem sunumda geriye gitmek yerine akıllıca `stay` kararı vererek mevcut konumunu korur.

### Durum 2: `Forward` (Gelecek Transkripte Doğrudan Atlama)

Bu durum, konuşmacının metinde ileriye doğru bir sıçrama yaptığı veya bazı kısımları atladığı durumları yönetir.

-   **Koşul:** `is_current_source` `False`'dur, yani eşleşen chunk mevcut transkriptten **değil**, gelecek bir transkripttendir.
-   **Mantık:** Sistem, "Beklediğim yer burası değil, konuşmacı ilerideki bir konuya geçmiş" sonucuna varır.
-   **Eylem:** Sistem, sunumu doğrudan eşleşen chunk'ın ait olduğu transkriptin slaytına ilerletir. Bu, sunumun konuşmacıyla senkronize kalmasını sağlar.

### Durum 3: `Forward` (`early_forward` Koşulunun Tetiklenmesi)

Bu, AutoSo'nun en gelişmiş karar mekanizmasıdır ve STT gecikmelerini telafi ederek pürüzsüz bir sunum deneyimi sunmak için tasarlanmıştır. Bu kararın verilebilmesi için aşağıdaki **üç koşulun da aynı anda** doğru olması gerekir:

1.  **`is_current_source` == `True`:** Eşleşme, mevcut transkript dahilindedir. Konuşmacı hala mevcut slaytın konusunu konuşmaktadır.
2.  **`current_transcript.get("early_forward", False)` == `True`:** Mevcut transkript, LLM tarafından "hızlı geçişe uygun" olarak işaretlenmiştir. Yani, özel bir bekleme gerektirmeyen, akıcı bir geçiş noktasıdır.
3.  **`is_next_source_different` == `True`:** Eşleşen chunk, mevcut transkriptin son kelimelerini içermektedir. Teknik olarak bu, bir sonraki chunk'ın kaynağının farklı bir `transcript_id` olmasıyla tespit edilir.

-   **Mantık:** Bu üç koşul bir araya geldiğinde, sistem şu sonuca varır: "Konuşmacı, hızlı geçişe uygun bir slaydın son cümlesini söyledi. Bir sonraki slaytın ilk kelimesini duymayı bekleyerek zaman kaybetmeye gerek yok."
-   **Eylem:** Sistem, proaktif bir şekilde `forward` kararı verir ve slaytı bir sonrakine geçirir. Bu, konuşmacı yeni slaytın ilk kelimesini söylediği anda, doğru slaydın zaten ekranda olmasını sağlar ve mükemmel bir senkronizasyon yaratır.

Bu üç katmanlı karar mekanizması, AutoSo'nun basit bir metin eşleştiriciden çok daha fazlası olmasını sağlar; onu, sunumun bağlamını anlayan ve akıllı kararlar verebilen otonom bir operatöre dönüştürür.