#!/usr/bin/env python3
"""
Test answer formatting to ensure no markdown symbols appear
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_answer_formatting():
    """Test that answers are generated without markdown symbols"""
    print("🧪 Testing Answer Formatting")
    print("=" * 40)
    
    try:
        from .llm_service import LLMService
        
        # Initialize LLM service
        llm_service = LLMService()
        print("✅ LLM service initialized")
        
        # Test prompt
        test_prompt = """
        Answer this question in simple terms: How many countries make up the UK?
        
        Provide a clear, educational answer suitable for rural Indian students.
        """
        
        print(f"\n📝 Test prompt: {test_prompt.strip()}")
        
        # Generate answer
        print("\n🔄 Generating answer...")
        answer = llm_service.generate_answer(test_prompt)
        
        print(f"\n📄 Generated answer:")
        print("-" * 50)
        print(answer)
        print("-" * 50)
        
        # Check for markdown symbols
        markdown_symbols = ['**', '*', '`', '#', '##', '###', '- ', '+ ']
        found_symbols = []
        
        for symbol in markdown_symbols:
            if symbol in answer:
                found_symbols.append(symbol)
        
        if found_symbols:
            print(f"\n❌ Found markdown symbols: {found_symbols}")
            print("The formatting cleanup needs improvement.")
            return False
        else:
            print(f"\n✅ No markdown symbols found!")
            print("Answer formatting is clean and readable.")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_answer_formatting()
    sys.exit(0 if success else 1) 