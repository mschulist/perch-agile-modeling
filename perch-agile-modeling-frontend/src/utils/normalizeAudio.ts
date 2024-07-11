export default function normalizeAudio(
    url: string,
    audioElem: HTMLAudioElement | null
) {
    const audioCtx = new AudioContext()

    if (!audioElem) {
        console.warn("No audio element found to normalize")
        return
    }

    const src = audioCtx.createMediaElementSource(audioElem)
    const gainNode = audioCtx.createGain()
    gainNode.gain.value = 1

    audioElem.addEventListener(
        "play",
        function () {
            src.connect(gainNode)
            gainNode.connect(audioCtx.destination)
        },
        true
    )
    audioElem.addEventListener(
        "pause",
        function () {
            // disconnect the nodes on pause, otherwise all nodes always run
            src.disconnect(gainNode)
            gainNode.disconnect(audioCtx.destination)
        },
        true
    )
    const proxyUrl = 'https://cors-anywhere.herokuapp.com/'
    fetch(proxyUrl + url)
        .then(function (res) {
            return res.arrayBuffer()
        })
        .then(function (buf) {
            return audioCtx.decodeAudioData(buf)
        })
        .then(function (decodedData) {
            var decodedBuffer = decodedData.getChannelData(0)
            var sliceLen = Math.floor(decodedData.sampleRate * 0.05)
            var averages = []
            var sum = 0.0
            for (var i = 0; i < decodedBuffer.length; i++) {
                sum += decodedBuffer[i] ** 2
                if (i % sliceLen === 0) {
                    sum = Math.sqrt(sum / sliceLen)
                    averages.push(sum)
                    sum = 0
                }
            }
            // Ascending sort of the averages array
            averages.sort(function (a, b) {
                return a - b
            })
            // Take the average at the 95th percentile
            var a = averages[Math.floor(averages.length * 0.95)]

            var gain = 1.0 / a

            gain = gain / 10.0
            console.log("gain determined", url, a, gain)
            gainNode.gain.value = gain
        })
}
