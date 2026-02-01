#!/usr/bin/env python3
"""
Voice Embedder using Pyannote.audio
Generates voice embeddings from audio segments for speaker identification.
"""

import os
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path


class VoiceEmbedder:
    """Generate voice embeddings using Pyannote.audio."""

    def __init__(self, model_name: str = 'pyannote/wespeaker-voxceleb-resnet34-LM'):
        """
        Initialize voice embedder.

        Args:
            model_name: Pyannote model to use for embeddings
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load Pyannote embedding model."""
        try:
            from pyannote.audio import Inference

            print(f"Loading Pyannote model: {self.model_name}")
            self.model = Inference(self.model_name)
            print("✓ Model loaded successfully")

        except ImportError:
            print("❌ pyannote.audio not installed")
            print("Install with: pip install pyannote-audio")
            raise

        except Exception as e:
            print(f"❌ Error loading Pyannote model: {e}")
            raise

    def generate_embedding(self, audio_file: str, start_time: float, end_time: float) -> Optional[np.ndarray]:
        """
        Generate voice embedding for audio segment.

        Args:
            audio_file: Path to audio file
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Embedding vector (numpy array) or None if failed
        """
        if self.model is None:
            print("❌ Model not loaded")
            return None

        try:
            # Extract audio segment
            audio_segment = self._extract_audio_segment(audio_file, start_time, end_time)

            if audio_segment is None:
                return None

            # Generate embedding using Pyannote
            embedding = self.model(audio_segment)

            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)

            return embedding

        except Exception as e:
            print(f"⚠️  Embedding generation failed: {e}")
            return None

    def _extract_audio_segment(self, audio_file: str, start_time: float, end_time: float) -> Optional[Dict]:
        """
        Extract audio segment for processing.

        Args:
            audio_file: Path to audio file
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Audio segment dict compatible with Pyannote or None if failed
        """
        try:
            import librosa

            # Load audio file
            audio, sr = librosa.load(audio_file, sr=16000, mono=True)

            # Extract segment
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)

            segment = audio[start_sample:end_sample]

            # Return in Pyannote-compatible format
            return {
                'waveform': segment,
                'sample_rate': sr
            }

        except ImportError:
            print("❌ librosa not installed")
            print("Install with: pip install librosa")
            return None

        except Exception as e:
            print(f"⚠️  Audio extraction failed: {e}")
            return None

    def generate_batch_embeddings(self, segments: List[Dict], audio_file: str) -> List[Optional[np.ndarray]]:
        """
        Generate embeddings for multiple segments from same audio file.

        Args:
            segments: List of segment dicts with 'start' and 'end' keys
            audio_file: Path to audio file

        Returns:
            List of embedding vectors (same order as segments)
        """
        embeddings = []

        for segment in segments:
            start = segment.get('start')
            end = segment.get('end')

            if start is None or end is None:
                embeddings.append(None)
                continue

            embedding = self.generate_embedding(audio_file, start, end)
            embeddings.append(embedding)

        return embeddings

    def average_embeddings(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """
        Average multiple embeddings to create robust speaker profile.

        Args:
            embeddings: List of embedding vectors

        Returns:
            Averaged embedding vector (L2 normalized)
        """
        # Filter out None values
        valid_embeddings = [e for e in embeddings if e is not None]

        if not valid_embeddings:
            raise ValueError("No valid embeddings to average")

        # Stack and average
        stacked = np.stack(valid_embeddings, axis=0)
        avg = np.mean(stacked, axis=0)

        # Normalize for cosine similarity
        avg = avg / np.linalg.norm(avg)

        return avg

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1, higher is more similar)
        """
        # Cosine similarity (assuming vectors are already normalized)
        similarity = np.dot(embedding1, embedding2)

        return float(similarity)
