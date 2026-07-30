"""
Blockchain Routes for Distributed Online Exam System
Handles blockchain-based result storage and verification
"""

import logging
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.blockchain import Blockchain, Block
from app.models import BlockchainBlock, User, Exam, Response
from app.services import ExamService

logger = logging.getLogger(__name__)

blockchain_bp = Blueprint('blockchain', __name__, url_prefix='/blockchain')

# Global blockchain instance
blockchain = Blockchain()

def save_blockchain_to_db():
    """Save blockchain to database"""
    try:
        # Clear existing blocks from database
        BlockchainBlock.query.delete()
        
        # Save all blocks to database
        for block in blockchain.chain:
            db_block = BlockchainBlock.from_block_object(block)
            db.session.add(db_block)
        
        db.session.commit()
        logger.info(f"Blockchain saved to database with {len(blockchain.chain)} blocks")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save blockchain to database: {e}")
        db.session.rollback()
        return False

def load_blockchain_from_db():
    """Load blockchain from database"""
    try:
        # Get all blocks from database ordered by index
        db_blocks = BlockchainBlock.query.order_by(BlockchainBlock.block_index).all()
        
        if not db_blocks:
            logger.info("No blocks found in database, using new blockchain")
            return
        
        # Convert to block dictionaries
        block_dicts = [db_block.to_dict() for db_block in db_blocks]
        
        # Reconstruct blockchain
        if blockchain.from_dict_list(block_dicts):
            logger.info(f"Blockchain loaded from database with {len(blockchain.chain)} blocks")
        else:
            logger.error("Failed to reconstruct blockchain from database")
            
    except Exception as e:
        logger.error(f"Failed to load blockchain from database: {e}")

def add_exam_result_to_blockchain(user_id: int, exam_id: int, score: float, 
                                  additional_data: dict = None) -> bool:
    """
    Add exam result to blockchain and save to database
    
    Args:
        user_id: ID of the user
        exam_id: ID of the exam
        score: Score achieved
        additional_data: Additional exam data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Add block to blockchain
        block = blockchain.add_block(user_id, exam_id, score, additional_data)
        
        # Save blockchain to database
        if save_blockchain_to_db():
            logger.info(f"Exam result added to blockchain - User: {user_id}, Exam: {exam_id}, Score: {score}")
            return True
        else:
            logger.error("Failed to save blockchain after adding block")
            return False
            
    except Exception as e:
        logger.error(f"Failed to add exam result to blockchain: {e}")
        return False

@blockchain_bp.route('/results')
@login_required
def view_results():
    """View all blockchain results"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get blockchain statistics
        stats = blockchain.get_chain_stats()
        
        # Get all blocks (excluding genesis block for display)
        blocks = [block.to_dict() for block in blockchain.chain[1:]]
        
        # Get user and exam information for each block
        for block in blocks:
            user = User.query.get(block['user_id'])
            exam = Exam.query.get(block['exam_id'])
            
            block['user_name'] = user.name if user else 'Unknown User'
            block['user_email'] = user.email if user else 'unknown@example.com'
            block['exam_title'] = exam.title if exam else 'Unknown Exam'
            block['exam_duration'] = exam.duration if exam else 0
        
        return render_template('blockchain_results.html', 
                             blocks=blocks, 
                             stats=stats,
                             total_blocks=len(blocks))
        
    except Exception as e:
        logger.error(f"Failed to view blockchain results: {e}")
        return jsonify({'error': 'Failed to view results'}), 500

@blockchain_bp.route('/api/results')
@login_required
def api_results():
    """API endpoint to get all blockchain results"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get all blocks (excluding genesis block)
        blocks = [block.to_dict() for block in blockchain.chain[1:]]
        
        # Add user and exam information
        for block in blocks:
            user = User.query.get(block['user_id'])
            exam = Exam.query.get(block['exam_id'])
            
            block['user_name'] = user.name if user else 'Unknown User'
            block['user_email'] = user.email if user else 'unknown@example.com'
            block['exam_title'] = exam.title if exam else 'Unknown Exam'
        
        return jsonify({
            'success': True,
            'blocks': blocks,
            'total_blocks': len(blocks),
            'stats': blockchain.get_chain_stats()
        })
        
    except Exception as e:
        logger.error(f"Failed to get blockchain results: {e}")
        return jsonify({'error': 'Failed to get results'}), 500

@blockchain_bp.route('/verify')
@login_required
def verify_blockchain():
    """Verify blockchain integrity"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Verify blockchain
        verification_result = blockchain.verify_chain()
        
        return jsonify({
            'success': True,
            'verification': verification_result
        })
        
    except Exception as e:
        logger.error(f"Failed to verify blockchain: {e}")
        return jsonify({'error': 'Failed to verify blockchain'}), 500

@blockchain_bp.route('/stats')
@login_required
def blockchain_stats():
    """Get blockchain statistics"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        stats = blockchain.get_chain_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Failed to get blockchain stats: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500

@blockchain_bp.route('/block/<int:block_index>')
@login_required
def get_block(block_index):
    """Get a specific block by index"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        block = blockchain.get_block_by_index(block_index)
        
        if not block:
            return jsonify({'error': 'Block not found'}), 404
        
        # Get user and exam information
        user = User.query.get(block.user_id)
        exam = Exam.query.get(block.exam_id)
        
        block_dict = block.to_dict()
        block_dict['user_name'] = user.name if user else 'Unknown User'
        block_dict['user_email'] = user.email if user else 'unknown@example.com'
        block_dict['exam_title'] = exam.title if exam else 'Unknown Exam'
        
        return jsonify({
            'success': True,
            'block': block_dict
        })
        
    except Exception as e:
        logger.error(f"Failed to get block: {e}")
        return jsonify({'error': 'Failed to get block'}), 500

@blockchain_bp.route('/user/<int:user_id>')
@login_required
def get_user_blocks(user_id):
    """Get all blocks for a specific user"""
    if not current_user.is_admin() and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        blocks = blockchain.get_blocks_by_user(user_id)
        
        # Add exam information
        block_dicts = []
        for block in blocks:
            exam = Exam.query.get(block.exam_id)
            block_dict = block.to_dict()
            block_dict['exam_title'] = exam.title if exam else 'Unknown Exam'
            block_dicts.append(block_dict)
        
        return jsonify({
            'success': True,
            'blocks': block_dicts,
            'total_blocks': len(block_dicts)
        })
        
    except Exception as e:
        logger.error(f"Failed to get user blocks: {e}")
        return jsonify({'error': 'Failed to get user blocks'}), 500

@blockchain_bp.route('/exam/<int:exam_id>')
@login_required
def get_exam_blocks(exam_id):
    """Get all blocks for a specific exam"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        blocks = blockchain.get_blocks_by_exam(exam_id)
        
        # Add user information
        block_dicts = []
        for block in blocks:
            user = User.query.get(block.user_id)
            block_dict = block.to_dict()
            block_dict['user_name'] = user.name if user else 'Unknown User'
            block_dict['user_email'] = user.email if user else 'unknown@example.com'
            block_dicts.append(block_dict)
        
        return jsonify({
            'success': True,
            'blocks': block_dicts,
            'total_blocks': len(block_dicts)
        })
        
    except Exception as e:
        logger.error(f"Failed to get exam blocks: {e}")
        return jsonify({'error': 'Failed to get exam blocks'}), 500

@blockchain_bp.route('/add_result', methods=['POST'])
@login_required
def add_result():
    """Add exam result to blockchain (for testing)"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        user_id = data.get('user_id')
        exam_id = data.get('exam_id')
        score = data.get('score')
        additional_data = data.get('additional_data', {})
        
        if not all([user_id, exam_id, score is not None]):
            return jsonify({'error': 'user_id, exam_id, and score are required'}), 400
        
        # Add result to blockchain
        if add_exam_result_to_blockchain(user_id, exam_id, score, additional_data):
            return jsonify({
                'success': True,
                'message': 'Result added to blockchain successfully'
            })
        else:
            return jsonify({'error': 'Failed to add result to blockchain'}), 500
        
    except Exception as e:
        logger.error(f"Failed to add result: {e}")
        return jsonify({'error': 'Failed to add result'}), 500

@blockchain_bp.route('/reset', methods=['POST'])
@login_required
def reset_blockchain():
    """Reset blockchain (for testing purposes)"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Clear blockchain and recreate genesis block
        blockchain.clear_chain()
        
        # Save to database
        if save_blockchain_to_db():
            logger.info("Blockchain reset successfully")
            return jsonify({
                'success': True,
                'message': 'Blockchain reset successfully'
            })
        else:
            return jsonify({'error': 'Failed to save reset blockchain'}), 500
        
    except Exception as e:
        logger.error(f"Failed to reset blockchain: {e}")
        return jsonify({'error': 'Failed to reset blockchain'}), 500

@blockchain_bp.route('/export')
@login_required
def export_blockchain():
    """Export blockchain as JSON"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get all blocks
        blocks = [block.to_dict() for block in blockchain.chain]
        
        return jsonify({
            'success': True,
            'blockchain': {
                'blocks': blocks,
                'stats': blockchain.get_chain_stats(),
                'exported_at': blockchain.get_chain_stats()['latest_block']['timestamp']
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to export blockchain: {e}")
        return jsonify({'error': 'Failed to export blockchain'}), 500

# Initialize blockchain from database when module loads
def init_blockchain():
    """Initialize blockchain from database"""
    load_blockchain_from_db()
    
    # If no blocks in database, save genesis block
    if BlockchainBlock.query.count() == 0:
        save_blockchain_to_db()

# Blockchain initialization will be done in app context
