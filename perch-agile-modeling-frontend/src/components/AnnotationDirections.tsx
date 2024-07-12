export default function AnnotationDirections() {
    return (
        <div className="text-gray-00">
            <p className="mb-4">
                <span className="text-red-500">Directions:</span> Click &ldquo;Get
                Next Recording&quot; to retrieve the next recording.
            </p>
            <p className="mb-4">
                <span className="text-blue-500">
                    Listen to the recording and identify the species shown below
                    the audio.
                </span>
            </p>
            <p className="mb-4">
                <span className="text-green-500">
                    Click on the appropriate vocalization type for that species.
                </span>
            </p>
            <p className="mb-4">
                <span className="text-yellow-500">
                    If the species of interest is not present in the recording,
                    simply move on to the next recording without labeling
                    anything.
                </span>
            </p>
            <p>
                <span className="text-purple-500">
                    Remember, we are only interested in a single species per
                    recording.
                </span>
            </p>
            <p className="mt-4">
                <span className="text-orange-500">
                    If nothing is vocalizing (e.g. just noise), please select
                    unknown.
                </span>
            </p>
            <p className="mt-4">
                <span className="text-red-500">
                    In an effort to limit incorrect labels, please only annotate
                    a recording if you are confident in your identification.
                </span>
            </p>
        </div>
    )
}
