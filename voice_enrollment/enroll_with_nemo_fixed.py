#!/usr/bin/env python3
"""
Voice Enrollment using Sherpa-ONNX Diarization + NeMo TitaNet Embeddings
Fixed version with configurable speaker detection
"""

import os
import sys
import json
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.committee_rosters import COMMITTEE_ROSTERS


class FixedSherpaDiarizer:
    """Sherpa diarizer with configurable speaker count."""
    
    def __init__(self, min_speakers=10, max_speakers=20):
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
    def diarize_audio(self, audio_path: str):
        """Run diarization with custom speaker counts."""
        import librosa
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics.pairwise import cosine_similarity
        from tqdm import tqdm
        
        print(f"🎯 Running diarization with {self.min_speakers}-{self.max_speakers} expected speakers...")
        
        # Load audio
        print("🎵 Loading audio...")
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        duration = len(audio) / sr
        
        # Create segments (5-second chunks)
        print("🔍 Creating speech segments...")
        segments = []
        segment_duration = 5.0
        for i in range(0, int(duration), int(segment_duration)):
            end_time = min(i + segment_duration, duration)
            if end_time - i >= 1.0:  # At least 1 second
                segments.append((float(i), float(end_time)))
        
        print(f"✅ Created {len(segments)} segments")
        
        # Extract MFCC features
        print("🔍 Extracting spectral features...")
        embeddings = []
        for start_time, end_time in tqdm(segments, desc="🎭 Analysis", unit="segment"):
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            segment_audio = audio[start_sample:end_sample]
            
            if len(segment_audio) < sr * 0.5:
                continue
                
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(y=segment_audio, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfccs, axis=1)
            
            # Additional features
            spectral_centroids = librosa.feature.spectral_centroid(y=segment_audio, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=segment_audio, sr=sr)
            zero_crossing_rate = librosa.feature.zero_crossing_rate(segment_audio)
            
            features = np.concatenate([
                mfcc_mean,
                [np.mean(spectral_centroids)],
                [np.mean(spectral_rolloff)],
                [np.mean(zero_crossing_rate)]
            ])
            
            embeddings.append(features)
        
        print(f"✅ Extracted {len(embeddings)} embeddings")
        
        # Cluster speakers with configurable count
        print(f"🧠 Clustering into {self.min_speakers}-{self.max_speakers} speakers...")
        embeddings_array = np.array(embeddings)
        
        # Calculate similarity
        similarity_matrix = cosine_similarity(embeddings_array)
        distance_matrix = 1 - similarity_matrix
        
        # Use hierarchical clustering with distance threshold to find optimal clusters
        # Start with max_speakers and see what we get
        n_clusters = min(self.max_speakers, max(self.min_speakers, len(embeddings) // 100))
        
        print(f"🎯 Targeting {n_clusters} speaker clusters...")
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            metric='precomputed',
            linkage='average'
        )
        
        labels = clustering.fit_predict(distance_matrix)
        
        unique_speakers = len(set(labels))
        print(f"✅ Identified {unique_speakers} unique speakers")
        
        # Map back to time segments
        result = []
        for i, (start_time, end_time) in enumerate(segments[:len(labels)]):
            speaker_id = labels[i]
            result.append((start_time, end_time, f"SPEAKER_{speaker_id:02d}"))
        
        print(f"🎉 Diarization complete!")
        return result


class NeMoEnrollment:
    """Voice enrollment using fixed Sherpa + NeMo TitaNet."""
    
    def __init__(self, min_speakers=10, max_speakers=20, temp_dir="voice_enrollment/temp"):
        self.temp_dir = temp_dir
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        # Load custom Sherpa with configurable speakers
        print(f"Initializing diarization ({min_speakers}-{max_speakers} speakers)...")
        self.diarizer = FixedSherpaDiarizer(min_speakers, max_speakers)
        print("✓ Diarization ready")
        
        # Load NeMo TitaNet
        print("Loading NeMo TitaNet...")
        self._load_nemo_model()
    
    def _load_nemo_model(self):
        """Load NeMo TitaNet speaker verification model."""
        try:
            from nemo.collections.asr.models import EncDecSpeakerLabelModel
            
            try:
                self.speaker_model = EncDecSpeakerLabelModel.from_pretrained(
                    "nvidia/speakerverification_en_titanet_large"
                )
                self.model_name = "titanet_large"
                print("✓ NeMo TitaNet-Large loaded")
                return
            except:
                self.speaker_model = EncDecSpeakerLabelModel.from_pretrained(
                    "nvidia/speakerverification_en_titanet_small"
                )
                self.model_name = "titanet_small"
                print("✓ NeMo TitaNet-Small loaded")
                return
        except Exception as e:
            raise RuntimeError(f"Could not load NeMo TitaNet: {e}")
    
    def diarize_meeting(self, audio_file: str) -> Dict:
        """Run diarization."""
        print(f"\n🎙️  Diarizing: {os.path.basename(audio_file)}")
        
        diarization = self.diarizer.diarize_audio(audio_file)
        
        if not diarization:
            return None
        
        # Group by speaker
        speaker_segments = defaultdict(list)
        for start_time, end_time, speaker_label in diarization:
            speaker_segments[speaker_label].append({
                'start': start_time,
                'end': end_time,
                'duration': end_time - start_time
            })
        
        print(f"\n   ✓ Detected {len(speaker_segments)} speakers")
        for speaker in sorted(speaker_segments.keys()):
            segments = speaker_segments[speaker]
            total_time = sum(s['duration'] for s in segments)
            print(f"   - {speaker}: {len(segments)} segments, {total_time:.1f}s total")
        
        return {
            'audio_file': audio_file,
            'speaker_segments': dict(speaker_segments),
            'num_speakers': len(speaker_segments)
        }
    
    def generate_speaker_embeddings(self, diarization_result: Dict, samples_per_speaker: int = 10) -> Dict:
        """Generate NeMo embeddings."""
        audio_file = diarization_result['audio_file']
        speaker_segments = diarization_result['speaker_segments']
        
        print(f"\n🔊 Generating NeMo TitaNet embeddings for {len(speaker_segments)} speakers...")
        
        speaker_embeddings = {}
        
        for speaker, segments in speaker_segments.items():
            print(f"   Processing {speaker}...")
            
            good_segments = [s for s in segments if 3.0 <= s['duration'] <= 10.0]
            
            if len(good_segments) < 2:
                print(f"      ⚠️  Insufficient segments ({len(good_segments)}/2)")
                continue
            
            import random
            sampled = random.sample(good_segments, min(samples_per_speaker, len(good_segments)))
            
            embeddings = []
            for segment in sampled:
                embedding = self._generate_nemo_embedding(
                    audio_file, segment['start'], segment['end']
                )
                if embedding is not None:
                    embeddings.append(embedding)
            
            if len(embeddings) >= 2:
                avg_embedding = self._average_embeddings(embeddings)
                
                speaker_embeddings[speaker] = {
                    'embedding': avg_embedding,
                    'sample_count': len(embeddings),
                    'segment_count': len(segments),
                    'total_duration': sum(s['duration'] for s in segments)
                }
                
                print(f"      ✓ Generated from {len(embeddings)} samples")
            else:
                print(f"      ⚠️  Failed ({len(embeddings)}/2)")
        
        return speaker_embeddings
    
    def _generate_nemo_embedding(self, audio_file: str, start_time: float, end_time: float) -> Optional[np.ndarray]:
        """Generate NeMo embedding."""
        try:
            import torch
            import librosa
            import soundfile as sf
            import tempfile
            
            audio, sr = librosa.load(audio_file, sr=16000, mono=True)
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            segment = audio[start_sample:end_sample]
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
                sf.write(temp_path, segment, 16000)
            
            try:
                embedding = self.speaker_model.get_embedding(temp_path)
                
                if torch.is_tensor(embedding):
                    embedding = embedding.cpu().detach().numpy()
                
                if len(embedding.shape) > 1:
                    embedding = embedding.flatten()
                
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass
        except Exception as e:
            print(f"      ⚠️  Failed: {e}")
            return None
    
    def _average_embeddings(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """Average embeddings."""
        stacked = np.stack(embeddings, axis=0)
        avg = np.mean(stacked, axis=0)
        return avg / np.linalg.norm(avg)
    
    def create_labeling_interface(self, speaker_embeddings: Dict, committee: str) -> Dict:
        """Interactive labeling."""
        print("\n" + "=" * 80)
        print("🏷️  SPEAKER LABELING INTERFACE")
        print("=" * 80)
        
        roster = COMMITTEE_ROSTERS.get(committee, [])
        
        if not roster:
            print(f"\n⚠️  No roster for: {committee}")
            return {}
        
        print(f"\nCommittee: {committee}")
        print(f"Roster: {len(roster)} members")
        print(f"Detected: {len(speaker_embeddings)} speakers")
        
        # Sort by speaking time
        sorted_speakers = sorted(
            speaker_embeddings.items(),
            key=lambda x: x[1]['total_duration'],
            reverse=True
        )
        
        print("\n📊 DETECTED SPEAKERS (by speaking time):")
        print("-" * 80)
        for speaker, data in sorted_speakers:
            print(f"{speaker}: {data['sample_count']} samples, "
                  f"{data['segment_count']} segments, "
                  f"{data['total_duration']:.1f}s total")
        
        print("\n👥 COMMITTEE ROSTER:")
        print("-" * 80)
        for idx, member in enumerate(roster, 1):
            print(f"{idx:2d}. {member['name']} ({member['party']}, Dist {member['district']})")
        
        print("\n" + "=" * 80)
        print("COMMANDS: 1-{} = member | skip = skip | done = finish".format(len(roster)))
        print("=" * 80)
        
        labeled_speakers = {}
        
        for speaker, data in sorted_speakers:
            print(f"\n🎤 {speaker}")
            print(f"   {data['sample_count']} samples, {data['total_duration']:.1f}s")
            
            while True:
                response = input(f"   Who? (1-{len(roster)}/skip/done): ").strip().lower()
                
                if response == 'done':
                    print("\n✓ Done")
                    return labeled_speakers
                
                if response == 'skip':
                    print(f"   ⊘ Skipping")
                    break
                
                try:
                    member_idx = int(response) - 1
                    if 0 <= member_idx < len(roster):
                        member = roster[member_idx]
                        labeled_speakers[speaker] = {
                            **member,
                            'embedding': data['embedding'],
                            'enrollment': {
                                'sample_count': data['sample_count'],
                                'segment_count': data['segment_count'],
                                'total_duration': data['total_duration'],
                                'original_speaker_label': speaker
                            }
                        }
                        print(f"   ✓ {member['name']}")
                        break
                    else:
                        print(f"   ❌ Invalid (1-{len(roster)})")
                except ValueError:
                    print(f"   ❌ Invalid input")
        
        return labeled_speakers
    
    def save_voice_database(self, labeled_speakers: Dict, meeting_file: str, output_file: str):
        """Save database."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        embedding_dim = len(next(iter(labeled_speakers.values()))['embedding']) if labeled_speakers else 192
        
        voice_db = {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'description': 'Voice database - Sherpa diarization + NeMo TitaNet',
            'diarization_method': 'sherpa-onnx-custom',
            'embedding_model': f'nvidia/speakerverification_en_{self.model_name}',
            'embedding_dim': embedding_dim,
            'source_meeting': meeting_file,
            'legislators': {}
        }
        
        for speaker_label, data in labeled_speakers.items():
            legislator_id = data['name'].lower().replace(' ', '_').replace('.', '')
            
            voice_db['legislators'][legislator_id] = {
                'name': data['name'],
                'chamber': data['chamber'],
                'district': data['district'],
                'party': data['party'],
                'committees': data['committees'],
                'embedding': data['embedding'].tolist(),
                'enrollment': data['enrollment']
            }
        
        with open(output_file, 'w') as f:
            json.dump(voice_db, f, indent=2)
        
        print(f"\n💾 Saved: {output_file}")
        print(f"   {len(voice_db['legislators'])} legislators")
        print(f"   Model: {self.model_name} ({embedding_dim}D)")
        
        # Summary
        summary_file = output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("VOICE DATABASE SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Created: {voice_db['created']}\n")
            f.write(f"Method: Sherpa + NeMo TitaNet\n")
            f.write(f"Model: {self.model_name} ({embedding_dim}D)\n")
            f.write(f"Source: {meeting_file}\n")
            f.write(f"Enrolled: {len(voice_db['legislators'])}\n\n")
            
            f.write("LEGISLATORS:\n")
            f.write("-" * 80 + "\n")
            
            for leg_data in sorted(voice_db['legislators'].values(), key=lambda x: x['name']):
                f.write(f"\n{leg_data['name']}\n")
                f.write(f"  {leg_data['chamber']} | Dist {leg_data['district']} | {leg_data['party']}\n")
                f.write(f"  Samples: {leg_data['enrollment']['sample_count']}\n")
                f.write(f"  Duration: {leg_data['enrollment']['total_duration']:.1f}s\n")
        
        print(f"📄 Summary: {summary_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Voice enrollment with configurable speaker detection')
    parser.add_argument('audio_file', help='Audio file path')
    parser.add_argument('--committee', required=True, choices=['HAFC', 'HJC', 'HRDLC'])
    parser.add_argument('--output', default='voice_enrollment/database/voice_database.json')
    parser.add_argument('--min-speakers', type=int, default=10, help='Minimum speakers (default: 10)')
    parser.add_argument('--max-speakers', type=int, default=20, help='Maximum speakers (default: 20)')
    parser.add_argument('--samples-per-speaker', type=int, default=10)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.audio_file):
        print(f"❌ Not found: {args.audio_file}")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("🎙️  VOICE ENROLLMENT - ENHANCED SPEAKER DETECTION")
    print("=" * 80)
    print(f"Audio: {args.audio_file}")
    print(f"Committee: {args.committee}")
    print(f"Expected speakers: {args.min_speakers}-{args.max_speakers}")
    print("=" * 80)
    
    try:
        enrollment = NeMoEnrollment(args.min_speakers, args.max_speakers)
    except Exception as e:
        print(f"\n❌ Init failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n📍 STEP 1: Diarization")
    result = enrollment.diarize_meeting(args.audio_file)
    
    if not result:
        print("\n❌ Diarization failed")
        sys.exit(1)
    
    print("\n📍 STEP 2: Generate Embeddings")
    embeddings = enrollment.generate_speaker_embeddings(result, args.samples_per_speaker)
    
    if not embeddings:
        print("\n❌ No embeddings")
        sys.exit(1)
    
    print("\n📍 STEP 3: Label Speakers")
    labeled = enrollment.create_labeling_interface(embeddings, args.committee)
    
    if not labeled:
        print("\n⚠️  No labels")
        sys.exit(1)
    
    print("\n📍 STEP 4: Save Database")
    enrollment.save_voice_database(labeled, args.audio_file, args.output)
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print(f"\n📂 Database: {args.output}")


if __name__ == '__main__':
    main()
