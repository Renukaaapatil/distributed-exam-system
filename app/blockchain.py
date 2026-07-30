"""
Blockchain-based Result Storage System for Distributed Online Exam System
Provides tamper-proof storage for exam results using cryptographic hashing
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class Block:
    """Represents a single block in the blockchain"""
    
    def __init__(self, index: int, timestamp: datetime, user_id: int, exam_id: int, 
                 score: float, previous_hash: str, data: Optional[Dict] = None):
        self.index = index
        self.timestamp = timestamp
        self.user_id = user_id
        self.exam_id = exam_id
        self.score = score
        self.previous_hash = previous_hash
        self.data = data or {}
        self.current_hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash for this block"""
        # Create block string representation
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'score': self.score,
            'previous_hash': self.previous_hash,
            'data': self.data
        }, sort_keys=True)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'score': self.score,
            'previous_hash': self.previous_hash,
            'current_hash': self.current_hash,
            'data': self.data
        }
    
    def __repr__(self):
        return f'<Block {self.index} - User: {self.user_id} - Exam: {self.exam_id} - Score: {self.score}>'

class Blockchain:
    """Blockchain class for managing exam result storage"""
    
    def __init__(self):
        self.chain: List[Block] = []
        self.difficulty = 2  # Mining difficulty (not used in this simple implementation)
        self.create_genesis_block()
        logger.info("Blockchain initialized with genesis block")
    
    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis_block = Block(
            index=0,
            timestamp=datetime.utcnow(),
            user_id=0,  # System user
            exam_id=0,  # System exam
            score=0.0,
            previous_hash="0" * 64,  # 64 zeros for genesis block
            data={
                'message': 'Genesis Block - Exam Result Blockchain',
                'created_by': 'Distributed Exam System',
                'version': '1.0'
            }
        )
        
        self.chain.append(genesis_block)
        logger.info("Genesis block created successfully")
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain"""
        return self.chain[-1] if self.chain else None
    
    def add_block(self, user_id: int, exam_id: int, score: float, 
                  additional_data: Optional[Dict] = None) -> Block:
        """
        Add a new block to the blockchain
        
        Args:
            user_id: ID of the user who took the exam
            exam_id: ID of the exam
            score: Score achieved by the user
            additional_data: Additional data to store with the result
            
        Returns:
            The newly created block
        """
        try:
            latest_block = self.get_latest_block()
            previous_hash = latest_block.current_hash if latest_block else "0" * 64
            
            # Prepare block data
            block_data = additional_data or {}
            block_data.update({
                'total_questions': additional_data.get('total_questions', 0) if additional_data else 0,
                'correct_answers': additional_data.get('correct_answers', 0) if additional_data else 0,
                'exam_duration': additional_data.get('exam_duration', 0) if additional_data else 0,
                'submission_time': datetime.utcnow().isoformat()
            })
            
            # Create new block
            new_block = Block(
                index=len(self.chain),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                exam_id=exam_id,
                score=score,
                previous_hash=previous_hash,
                data=block_data
            )
            
            # Add block to chain
            self.chain.append(new_block)
            
            logger.info(f"Block added successfully - Index: {new_block.index}, "
                       f"User: {user_id}, Exam: {exam_id}, Score: {score}")
            
            return new_block
            
        except Exception as e:
            logger.error(f"Failed to add block: {e}")
            raise
    
    def hash_block(self, block: Block) -> str:
        """
        Calculate hash for a specific block
        
        Args:
            block: Block to hash
            
        Returns:
            SHA-256 hash of the block
        """
        return block.calculate_hash()
    
    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the integrity of the entire blockchain
        
        Returns:
            Dictionary with verification results
        """
        try:
            results = {
                'valid': True,
                'issues': [],
                'total_blocks': len(self.chain),
                'verified_at': datetime.utcnow().isoformat()
            }
            
            # Check if chain is empty
            if not self.chain:
                results['valid'] = False
                results['issues'].append('Blockchain is empty')
                return results
            
            # Verify each block in the chain
            for i in range(1, len(self.chain)):
                current_block = self.chain[i]
                previous_block = self.chain[i - 1]
                
                # Check if previous hash matches
                if current_block.previous_hash != previous_block.current_hash:
                    results['valid'] = False
                    results['issues'].append(
                        f"Block {i}: Previous hash mismatch. "
                        f"Expected: {previous_block.current_hash}, "
                        f"Found: {current_block.previous_hash}"
                    )
                
                # Check if current hash is correct
                calculated_hash = self.hash_block(current_block)
                if current_block.current_hash != calculated_hash:
                    results['valid'] = False
                    results['issues'].append(
                        f"Block {i}: Current hash mismatch. "
                        f"Expected: {calculated_hash}, "
                        f"Found: {current_block.current_hash}"
                    )
                
                # Check block index sequence
                if current_block.index != i:
                    results['valid'] = False
                    results['issues'].append(
                        f"Block {i}: Index mismatch. Expected: {i}, Found: {current_block.index}"
                    )
            
            if results['valid']:
                logger.info("Blockchain verified: No tampering detected")
            else:
                logger.warning(f"Blockchain verification failed: {len(results['issues'])} issues found")
            
            return results
            
        except Exception as e:
            logger.error(f"Error verifying blockchain: {e}")
            return {
                'valid': False,
                'issues': [f"Verification error: {str(e)}"],
                'total_blocks': len(self.chain),
                'verified_at': datetime.utcnow().isoformat()
            }
    
    def get_block_by_index(self, index: int) -> Optional[Block]:
        """Get a specific block by its index"""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None
    
    def get_blocks_by_user(self, user_id: int) -> List[Block]:
        """Get all blocks for a specific user"""
        return [block for block in self.chain if block.user_id == user_id]
    
    def get_blocks_by_exam(self, exam_id: int) -> List[Block]:
        """Get all blocks for a specific exam"""
        return [block for block in self.chain if block.exam_id == exam_id]
    
    def get_chain_stats(self) -> Dict:
        """Get statistics about the blockchain"""
        if not self.chain:
            return {
                'total_blocks': 0,
                'genesis_block': None,
                'latest_block': None,
                'unique_users': 0,
                'unique_exams': 0,
                'average_score': 0.0
            }
        
        # Calculate statistics
        unique_users = len(set(block.user_id for block in self.chain if block.user_id > 0))
        unique_exams = len(set(block.exam_id for block in self.chain if block.exam_id > 0))
        
        # Calculate average score (excluding genesis block)
        score_blocks = [block for block in self.chain if block.user_id > 0]
        average_score = sum(block.score for block in score_blocks) / len(score_blocks) if score_blocks else 0.0
        
        return {
            'total_blocks': len(self.chain),
            'genesis_block': self.chain[0].to_dict(),
            'latest_block': self.chain[-1].to_dict(),
            'unique_users': unique_users,
            'unique_exams': unique_exams,
            'average_score': round(average_score, 2),
            'chain_length': len(self.chain)
        }
    
    def to_dict_list(self) -> List[Dict]:
        """Convert entire blockchain to list of dictionaries"""
        return [block.to_dict() for block in self.chain]
    
    def from_dict_list(self, block_dicts: List[Dict]) -> bool:
        """
        Reconstruct blockchain from list of block dictionaries
        
        Args:
            block_dicts: List of block dictionaries
            
        Returns:
            True if reconstruction successful, False otherwise
        """
        try:
            self.chain = []
            
            for block_dict in block_dicts:
                # Convert timestamp back to datetime
                timestamp = datetime.fromisoformat(block_dict['timestamp'])
                
                # Create block
                block = Block(
                    index=block_dict['index'],
                    timestamp=timestamp,
                    user_id=block_dict['user_id'],
                    exam_id=block_dict['exam_id'],
                    score=block_dict['score'],
                    previous_hash=block_dict['previous_hash'],
                    data=block_dict.get('data', {})
                )
                
                # Verify hash matches
                if block.current_hash != block_dict['current_hash']:
                    logger.error(f"Hash mismatch for block {block.index}")
                    return False
                
                self.chain.append(block)
            
            logger.info(f"Blockchain reconstructed from {len(block_dicts)} blocks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reconstruct blockchain: {e}")
            return False
    
    def clear_chain(self):
        """Clear the blockchain (for testing purposes)"""
        self.chain = []
        self.create_genesis_block()
        logger.info("Blockchain cleared and genesis block recreated")
    
    def __len__(self):
        """Get the length of the blockchain"""
        return len(self.chain)
    
    def __repr__(self):
        return f'<Blockchain with {len(self.chain)} blocks>'
