# Gerçek Zamanlı Akış (Streaming) ASR/STT Sistemi

## Giriş

AutoSo'nun anlık ve kesintisiz çalışabilmesinin arkasındaki teknoloji, gerçek zamanlı bir ses işleme ve konuşma tanıma (ASR/STT) hattıdır. Bu sistem, `app.py` içerisinde, birbirine bağlı ancak bağımsız çalışan bileşenler aracılığıyla, sesi yakaladığı andan navigasyon kararı verdiği ana kadar olan süreci minimum gecikmeyle yönetir. Bu yapı, yüksek performans ve yanıt verme yeteneği için tasarlanmıştır.

## Sistem Mimarisi ve Bileşenler

Sistem, görevleri birbirinden ayıran ve paralel olarak çalışmasını sağlayan **çoklu iş parçacığı (multi-threaded)** ve **kuyruk (queue)** tabanlı bir mimari kullanır.

-   **İş Parçacıkları (Threads):**
    1.  **`AudioStreamer`:** (Ana iş parçacığında çalışır) Mikrofondan ses verisini yakalar ve ses aktivitesini denetler.
    2.  **`RecognizerWorker`:** Gelen ses verisini metne dönüştürmekten sorumlu arka plan işçisidir.
    3.  **`NavigationWorker`:** Metne dönüştürülmüş veriyi alıp navigasyon kararlarını üretmekten sorumlu arka plan işçisidir.

-   **Kuyruklar (Queues):**
    1.  **`audio_queue`:** `AudioStreamer`'ın, içinde konuşma tespit ettiği ses paketlerini koyduğu kuyruktur. `RecognizerWorker` bu kuyruktan veri çeker.
    2.  **`speech_queue`:** `RecognizerWorker`'ın, metne dönüştürdüğü ifadeleri koyduğu kuyruktur. `NavigationWorker` bu kuyruktan veri çeker.
    Bu kuyruklar, her bir bileşenin diğerini beklemeden kendi görevini yapmasını sağlayarak sistemi akıcı ve verimli hale getirir.

-   **Temel Kütüphaneler:**
    -   `sounddevice`: Düşük seviyeli ses girişi ve çıkışı için kullanılır.
    -   `webrtcvad`: Yüksek hassasiyetli ses aktivitesi tespiti (Voice Activity Detection - VAD) için kullanılır.
    -   `vosk`: Yerel (offline), hafif ve hızlı konuşma tanıma motorudur.
    -   `keyboard`: Sunum yazılımını kontrol etmek için sanal klavye komutları göndermeyi sağlar.

## Adım Adım Ses Akışı

Kullanıcı `SPACE` tuşuna bastığı andan itibaren ses verisi aşağıdaki yedi adımlık yolculuğu tamamlar:

**Adım 1: Ses Yakalama (`AudioStreamer`)**
-   `sounddevice` kütüphanesi aracılığıyla, sistem varsayılan mikrofondan sürekli olarak ham ses verisini yakalamaya başlar. Ses, `FRAME_DURATION` (örn: 0.2 saniye) uzunluğunda küçük paketler halinde alınır.

**Adım 2: Ses Aktivitesi Tespiti - VAD (`webrtcvad`)**
-   Yakalanan her ses paketi, anında `webrtcvad` motoruna gönderilir. Bu motor, paketin içinde insan konuşması mı yoksa sessizlik/arka plan gürültüsü mü olduğunu tespit eder.
-   **Bu adım kritiktir:**
    -   Eğer **sessizlik** tespit edilirse, ses paketi anında **atılır**. Bu, işlemcinin gereksiz yere meşgul edilmesini önler ve sadece anlamlı ses verisinin işlenmesini sağlayarak sistemin verimliliğini katbekat artırır.
    -   Eğer **konuşma** tespit edilirse, ses paketi bir sonraki adıma geçirilir.

**Adım 3: Sesin Kuyruğa Eklenmesi**
-   İçinde konuşma olduğu onaylanan ses paketi, bayt dizisi (byte array) olarak `audio_queue`'ya eklenir.

**Adım 4: Konuşma Tanıma (`RecognizerWorker`)**
-   Bu arka plan işçisi, sürekli olarak `audio_queue`'yu dinler.
-   Kuyruğa yeni bir ses paketi geldiği anda, bu paketi çeker ve `Vosk`'un `KaldiRecognizer` motoruna `AcceptWaveform` metoduyla besler.
-   Vosk motoru, gelen ses verisini işleyerek bir `PartialResult` (kısmi sonuç) üretir. Bu, konuşma devam ederken anlık olarak güncellenen, henüz kesinleşmemiş bir metin transkripsiyonudur.

**Adım 5: Metnin Kuyruğa Eklenmesi**
-   Vosk'tan gelen bu anlık ve kısmi metin, `speech_queue`'ya eklenir.

**Adım 6: Navigasyon (`NavigationWorker`)**
-   Bu ikinci arka plan işçisi, `speech_queue`'yu dinler.
-   Kuyruğa yeni bir metin geldiği anda, bu metni çeker ve `RealtimeNavigator`'ın `navigate` metoduna gönderir.
-   Navigator, gelen metni kullanarak [Benzerlik Algoritmaları](./similarity_algorithms.md) ile en iyi eşleşen chunk'ı bulur ve [Navigasyon Karar Algoritması](./navigation_decisions.md) ile nihai kararını (`stay` veya `forward`) verir.

**Adım 7: Eylem (`keyboard`)**
-   `NavigationWorker`, Navigator'dan dönen sonucu analiz eder.
-   Eğer karar `forward` ise, `keyboard.press_and_release("right")` komutuyla sunum yazılımına sanal bir "sağ ok" tuşuna basma sinyali gönderilir ve slayt ilerler.
-   Eğer karar `stay` ise, hiçbir eylemde bulunulmaz.

Bu akış şeması, sistemin neden bu kadar hızlı ve yanıt verebilir olduğunu gösterir. Her bir adım, bir sonrakini beklemeden çalışır ve veriler kuyruklar aracılığıyla asenkron bir şekilde akar. Bu, minimum gecikme ile maksimum performans sağlar.

### Akış Şeması

```
[Mikrofon]
    |
    v
[AudioStreamer] --(VAD ile Filtreleme)--> [Sessizlik ise ATILIR]
    |
(Konuşma varsa)
    |
    v
[audio_queue]
    |
    v
[RecognizerWorker] --(Vosk ile Metne Çevirme)-->
    |
    v
[speech_queue]
    |
    v
[NavigationWorker] --(Navigator ile Karar Verme)-->
    |
    v
[Klavye Eylemi: stay/forward]
```