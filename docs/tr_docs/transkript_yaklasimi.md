# Transcript Üretim Yaklaşımı

## Giriş

AutoSo sisteminin temel taşı **Transcript** veri yapısıdır. Transcript, bir sunumun konuşma metnini, slaytlarla senkronize bir şekilde, yapılandırılmış ve sıralı bir biçimde temsil eder. Bu yapı olmadan, sistemin konuşmacıyı takip etmesi ve doğru navigasyon kararları vermesi imkansızdır.

Bu belgede, `transcript_generator.py` dosyasında uygulanan ve bir sunumun ham PDF dosyalarından başlayarak bu kritik veri yapısının nasıl oluşturulduğu adım adım açıklanmaktadır.

## Süreç Akışı

Transcript üretimi, `TranscriptGenerator` sınıfı tarafından yönetilen çok adımlı bir süreçtir. Bu süreç, ham verilerin çıkarılmasından, bir dil modeli (LLM) ile zenginleştirilmesine ve son olarak sistemin kullanabileceği nihai JSON formatına dönüştürülmesine kadar uzanır.

### Adım 1: Girdi Verileri

Süreç, her bir sunum için iki temel PDF dosyasıyla başlar:

1.  **Slayt Dosyası (`input_path_slide`):** İzleyicilerin ekranda gördüğü, genellikle az metin içeren görsel sunum dosyasıdır. (Örn: `ezgi_slide.pdf`)
2.  **Metin Dosyası (`input_path_text`):** Konuşmacının okuduğu veya referans aldığı, sunumun tam metnini içeren dosyadır. (Örn: `ezgi_text.pdf`)

### Adım 2: Veri Çıkarımı ve Normalizasyon (`_extract_data` metodu)

Bu adımda, `PyMuPDF (fitz)` kütüphanesi kullanılarak PDF dosyalarındaki metinler çıkarılır ve ön işleme tabi tutulur.

-   **Slayt Verisi İşleme:**
    -   Her bir slayt sayfası ayrı ayrı okunur.
    -   Sayfa numaraları anahtar (key), sayfa içeriği ise değer (value) olacak şekilde bir sözlük (dictionary) oluşturulur.
    -   Örnek Çıktı: `{"1": "the ability to say no", "2": "have you ever struggled when you tried to say no"}`

-   **Metin Verisi İşleme:**
    -   Metin dosyasındaki tüm sayfalar okunur.
    -   Sayfalardaki metinler birleştirilerek tek ve uzun bir metin bloğu (string) oluşturulur.
    -   Örnek Çıktı: `"the ability to say no have you ever struggled when you tried to say no to someone"`

-   **Metin Normalizasyonu (`_normalize_text` metodu):**
    -   Çıkarılan tüm metinler, tutarlılığı sağlamak için bir normalizasyon sürecinden geçer. Bu süreçte:
        -   Tüm harfler küçük harfe çevrilir.
        -   Unicode karakterler standart forma (`NFC`) getirilir.
        -   Tüm noktalama işaretleri kaldırılır.
        -   Tire (`-`) gibi karakterler boşlukla değiştirilir.

### Adım 3: LLM ile Yapılandırma ve Zenginleştirme (`_process_with_llm` metodu)

Bu, sürecin en kritik ve en "akıllı" adımıdır. Slayt metinleri ile tam konuşma metni, bir dil modeline (LLM) gönderilerek anlamlı ve sıralı transkriptlere dönüştürülür.

-   **Kullanılan Teknolojiler:**
    -   **LiteLLM:** Bu kütüphane, farklı LLM sağlayıcılarını (OpenAI, Gemini, Mistral vb.) tek bir arayüz altında soyutlar. Bu sayede sistem, `GEMINI_API_KEY` ortam değişkeniyle varsayılan olarak `gemini-2.0-flash` modelini kullanır, ancak kolayca başka bir modele geçirilebilir.
    -   **Instructor:** Bu kütüphane, LiteLLM'i yamalayarak LLM'den dönen cevabın, önceden tanımlanmış bir Pydantic modeline tam olarak uymasını zorunlu kılar. Bu, LLM'in halüsinasyon görmesi veya formatı bozması gibi sorunları ortadan kaldırır ve veri bütünlüğünü garanti eder.

-   **Pydantic Modeli (`TranscriptItem`):**
    LLM'in uyması gereken yapı şu şekilde tanımlanmıştır:
    ```python
    class TranscriptItem(BaseModel):
        transcript_index: int
        transcript: str
        early_forward: bool
    ```

-   **`early_forward` Bayrağının Rolü:**
    LLM'den, her bir transkript parçası için bu bayrağı `true` veya `false` olarak ayarlaması istenir. Bu bayrak, navigasyon algoritmasının akıcılığını doğrudan etkiler.
    -   **`False` Durumu:** LLM, konuşmacının bir soru soracağı ("elleri göreyim"), bir duraksama yaşayacağı veya seyirciyle etkileşime gireceği metinleri tespit ettiğinde bu değeri seçer. Bu, navigasyonun o noktada beklemesi gerektiğini belirtir.
    -   **`True` Durumu:** LLM, konuşmanın normal bir akışla devam ettiğini ve özel bir bekleme gerektirmediğini anladığında bu değeri seçer. Bu, navigasyonun proaktif olarak bir sonraki slayta geçebileceğini belirtir.

### Adım 4: Son İşlemler ve Kayıt

1.  **Benzersiz Kimlik Ataması:** LLM'den gelen her bir transkript öğesine, `fastnanoid` kütüphanesi kullanılarak benzersiz bir `transcript_id` atanır. Bu kimlik, daha sonra chunk'ların kaynağını belirlemek için kullanılır.
2.  **İndekslerin Yeniden Düzenlenmesi:** LLM'in verdiği `transcript_index` değerleri, sadece LLM'in görevini doğru yapmasını sağlamak içindir. Bu adımda bu indeksler atılır ve tüm transkript listesi 0'dan başlayarak yeniden indekslenir. Bu, sistemin tutarlı bir dizi indeksiyle çalışmasını sağlar.
3.  **Kayıt:** Tamamlanan transkript listesi, `orjson` kütüphanesi kullanılarak `kullanici_adi_transcript.json` adıyla, girintili ve okunaklı bir formatta kaydedilir.

### Nihai Çıktı

Tüm bu sürecin sonunda, aşağıdaki gibi yüksek kaliteli ve yapılandırılmış bir veri elde edilir:
```json
[
  {
    "transcript_index": 0,
    "transcript_id": "iqM_H_XCm0rUW_46obYGl",
    "transcript": "the ability to say no",
    "early_forward": true
  },
  {
    "transcript_index": 1,
    "transcript_id": "L9LPKs2roR5FOS6HhPiRP",
    "transcript": "have you ever struggled when you tried to say no to someone",
    "early_forward": true
  },
  {
    "transcript_index": 2,
    "transcript_id": "VIf3Xfh6hTseWFS3zaTuU",
    "transcript": "or perhaps you couldnt say no to a person because you felt bad for them",
    "early_forward": true
  }
]
```
Bu dosya, bir sonraki adım olan **Chunk Üretimi** için girdi görevi görür.