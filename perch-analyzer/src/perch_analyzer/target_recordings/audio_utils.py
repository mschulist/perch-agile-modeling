"""Audio utilities.

General utilities for processing audio and spectrograms.

Taken directly from the Perch repository
"""

from . import signal
from jax import numpy as jnp
from jax import scipy as jsp
from jax.typing import ArrayLike
from scipy import signal as scipy_signal


def pad_to_length_if_shorter(audio: jnp.ndarray, target_length: int):
    """Wraps the audio sequence if it's shorter than the target length.

    Args:
      audio: input audio sequence of shape [num_samples].
      target_length: target sequence length.

    Returns:
      The audio sequence, padded through wrapping (if it's shorter than the target
      length).
    """
    if audio.shape[0] < target_length:
        missing = target_length - audio.shape[0]
        pad_left = missing // 2
        pad_right = missing - pad_left
        audio = jnp.pad(audio, [[pad_left, pad_right]], mode="wrap")
    return audio


def slice_peaked_audio(
    audio: ArrayLike,
    sample_rate_hz: int,
    interval_length_s: float = 6.0,
    max_intervals: int = 5,
) -> jnp.ndarray:
    """Extracts audio intervals from melspec peaks.

    Args:
      audio: input audio sequence of shape [num_samples].
      sample_rate_hz: sample rate of the audio sequence (Hz).
      interval_length_s: length each extracted audio interval.
      max_intervals: upper-bound on the number of audio intervals to extract.

    Returns:
      Sequence of start and stop indices for the extracted audio intervals.
    """
    target_length = int(sample_rate_hz * interval_length_s)

    # Wrap audio to the target length if it's shorter than that.
    audio = pad_to_length_if_shorter(audio, target_length)  # type: ignore

    peaks = find_peaks_from_audio(audio, sample_rate_hz, max_intervals)
    left_shift = target_length // 2
    right_shift = target_length - left_shift

    # Ensure that the peak locations are such that
    # `audio[peak - left_shift: peak + right_shift]` is a non-truncated slice.
    peaks = jnp.clip(peaks, left_shift, jnp.array(audio).shape[0] - right_shift)
    # As a result, it's possible that some (start, stop) pairs become identical;
    # eliminate duplicates.
    start_stop = jnp.unique(
        jnp.stack([peaks - left_shift, peaks + right_shift], axis=-1), axis=0
    )

    return start_stop


def find_peaks_from_audio(
    audio: jnp.ndarray,
    sample_rate_hz: int,
    max_peaks: int,
    num_mel_bins: int = 160,
) -> jnp.ndarray:
    """Construct melspec and find peaks.

    Args:
      audio: input audio sequence of shape [num_samples].
      sample_rate_hz: sample rate of the audio sequence (Hz).
      max_peaks: upper-bound on the number of peaks to return.
      num_mel_bins: The number of mel-spectrogram bins to use.

    Returns:
      Sequence of scalar indices for the peaks found in the audio sequence.
    """
    melspec_rate_hz = 100
    frame_length_s = 0.08
    nperseg = int(frame_length_s * sample_rate_hz)
    nstep = sample_rate_hz // melspec_rate_hz
    _, _, spectrogram = jsp.signal.stft(
        audio, nperseg=nperseg, noverlap=nperseg - nstep
    )
    # apply_mixture_denoising/find_peaks_from_melspec expect frequency axis last
    spectrogram = jnp.swapaxes(spectrogram, -1, -2)
    magnitude_spectrogram = jnp.abs(spectrogram)

    # For backwards compatibility, we scale the spectrogram here the same way
    # that the TF spectrogram is scaled. If we don't, the values are too small and
    # end up being clipped by the default configuration of the logarithmic scaling
    magnitude_spectrogram *= nperseg / 2

    # Construct mel-spectrogram
    num_spectrogram_bins = magnitude_spectrogram.shape[-1]
    mel_matrix = signal.linear_to_mel_weight_matrix(
        num_mel_bins,
        num_spectrogram_bins,
        sample_rate_hz,
        lower_edge_hertz=60,
        upper_edge_hertz=10_000,
    )
    mel_spectrograms = magnitude_spectrogram @ mel_matrix

    melspec = log_scale(mel_spectrograms, floor=1e-2, offset=0.0, scalar=0.1)
    melspec = apply_mixture_denoising(melspec, 0.75)

    peaks = find_peaks_from_melspec(melspec, melspec_rate_hz)
    peak_energies = jnp.sum(melspec, axis=1)[peaks]

    def t_mel_to_t_au(tm):
        return 1.0 * tm * sample_rate_hz / melspec_rate_hz

    peaks = [t_mel_to_t_au(p) for p in peaks]

    peak_set = sorted(zip(peak_energies, peaks), reverse=True)
    if max_peaks > 0 and len(peaks) > max_peaks:
        peak_set = peak_set[:max_peaks]
    return jnp.asarray([p[1] for p in peak_set], dtype=jnp.int32)


def find_peaks_from_melspec(melspec: jnp.ndarray, stft_fps: int) -> jnp.ndarray:
    """Locate peaks inside signal of summed spectral magnitudes.

    Args:
      melspec: input melspectrogram of rank 2 (time, frequency).
      stft_fps: Number of summed magnitude bins per second. Calculated from the
        original sample of the waveform.

    Returns:
      A list of filtered peak indices.
    """
    summed_spectral_magnitudes = jnp.sum(melspec, axis=1)
    threshold = jnp.mean(summed_spectral_magnitudes) * 1.5
    min_width = int(round(0.5 * stft_fps))
    max_width = int(round(2 * stft_fps))
    width_step_size = int(round((max_width - min_width) / 10))
    peaks = scipy_signal.find_peaks_cwt(
        summed_spectral_magnitudes,
        jnp.arange(min_width, max_width, width_step_size),
    )
    margin_frames = int(round(0.3 * stft_fps))
    start_stop = jnp.clip(
        jnp.stack([peaks - margin_frames, peaks + margin_frames], axis=-1),
        0,
        summed_spectral_magnitudes.shape[0],
    )
    peaks = [
        p
        for p, (a, b) in zip(peaks, start_stop)
        if summed_spectral_magnitudes[a:b].max() >= threshold
    ]
    return jnp.asarray(peaks, dtype=jnp.int32)


def log_scale(
    x: jnp.ndarray, floor: float, offset: float, scalar: float
) -> jnp.ndarray:
    """Apply log-scaling.

    Args:
      x: The data to scale.
      floor: Clip input values below this value. This avoids taking the logarithm
        of negative or very small numbers.
      offset: Shift all values by this amount, after clipping. This too avoids
        taking the logarithm of negative or very small numbers.
      scalar: Scale the output by this value.

    Returns:
      The log-scaled data.
    """
    x = jnp.log(jnp.maximum(x, floor) + offset)
    return scalar * x


def apply_mixture_denoising(melspec: jnp.ndarray, threshold: float) -> jnp.ndarray:
    """Denoises the melspectrogram using an estimated Gaussian noise distribution.

    Forms a noise estimate by a) estimating mean+std, b) removing extreme
    values, c) re-estimating mean+std for the noise, and then d) classifying
    values in the spectrogram as 'signal' or 'noise' based on likelihood under
    the revised estimate. We then apply a mask to return the signal values.

    Args:
      melspec: input melspectrogram of rank 2 (time, frequency).
      threshold: z-score theshold for separating signal from noise. On the first
        pass, we use 2 * threshold, and on the second pass we use threshold
        directly.

    Returns:
      The denoised melspectrogram.
    """
    x = melspec
    feature_mean = jnp.mean(x, axis=0, keepdims=True)
    feature_std = jnp.std(x, axis=0, keepdims=True)
    is_noise = (x - feature_mean) < 2 * threshold * feature_std

    noise_counts = jnp.sum(is_noise.astype(x.dtype), axis=0, keepdims=True)
    noise_mean = jnp.sum(x * is_noise, axis=0, keepdims=True) / (noise_counts + 1)
    noise_var = jnp.sum(is_noise * jnp.square(x - noise_mean), axis=0, keepdims=True)
    noise_std = jnp.sqrt(noise_var / (noise_counts + 1))

    # Recompute signal/noise separation.
    demeaned = x - noise_mean
    is_signal = demeaned >= threshold * noise_std
    is_signal = is_signal.astype(x.dtype)
    is_noise = 1.0 - is_signal

    signal_part = is_signal * x
    noise_part = is_noise * noise_mean
    reconstructed = signal_part + noise_part - noise_mean
    return reconstructed