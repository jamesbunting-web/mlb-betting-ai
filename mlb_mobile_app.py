#!/usr/bin/env python3
"""
MLB Betting AI Agent - Mobile Web App
Full-featured Flask app with beautiful mobile UI
YOUR ODDS API KEY: 53f7a9f44c53d8c8963bac45f9ea65b8
"""

from flask import Flask, render_template, request, jsonify
from mlb_ai_agent_v2_full_auto import MLBBettingAgentFullAuto
from datetime import datetime
import json
import os

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Store the latest analysis result in memory (simple cache)
latest_results = {}

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('mobile_app.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Run full auto analysis"""
    try:
        data = request.json
        odds_api_key = data.get('odds_api_key', '53f7a9f44c53d8c8963bac45f9ea65b8')  # Your key as default
        
        if not odds_api_key:
            return jsonify({'error': 'Odds API key required'}), 400
        
        # Run agent
        agent = MLBBettingAgentFullAuto(odds_api_key)
        results = agent.full_auto_analysis(odds_api_key)
        
        # Cache results
        latest_results['data'] = results
        latest_results['timestamp'] = datetime.now().isoformat()
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/latest', methods=['GET'])
def get_latest():
    """Get latest cached results"""
    if 'data' in latest_results:
        return jsonify(latest_results['data'])
    return jsonify({'error': 'No results cached'}), 404

@app.route('/api/framework', methods=['GET'])
def get_framework():
    """Get framework info"""
    return jsonify({
        '1A': {'odds': '+115-+125', 'threshold': 5.0, 'units': '1.0U elite / 0.5U solid'},
        '1B': {'odds': '+130-+145', 'threshold': 4.5, 'units': '1.0U elite / 0.5U solid'},
        '2': {'odds': '+150-+165', 'threshold': 4.0, 'units': '0.5U'},
        '3': {'odds': '+170-+185', 'threshold': 3.5, 'units': '0.25U'}
    })

@app.route('/api/help', methods=['GET'])
def get_help():
    """Get help documentation"""
    return jsonify({
        'title': 'MLB Betting AI Agent',
        'description': 'Fully automated scoring with MLB Stats API + Odds API',
        'workflow': [
            'App loads with your Odds API key pre-filled',
            'Click "Analyze Today\'s Games"',
            'Agent fetches schedule + odds automatically',
            'Agent identifies plays in +115-+185 range',
            'Agent pulls rest days + injuries',
            'Agent scores all 9 factors',
            'Agent ranks qualified plays by score',
            'Review results + place bets'
        ]
    })

if __name__ == '__main__':
    print("\n" + "="*100)
    print("MLB BETTING AI AGENT - MOBILE WEB APP")
    print("="*100)
    print("\nStarting server...")
    print("\nAccess on your phone/computer:")
    print("  Local: http://localhost:5000")
    print("\n" + "="*100 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
