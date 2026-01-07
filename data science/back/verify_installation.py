
import sys
import importlib

def check_import(module_name, display_name=None):
    if display_name is None:
        display_name = module_name
    try:
        importlib.import_module(module_name)
        print(f"✅ {display_name} installed and importable.")
        return True
    except ImportError as e:
        print(f"❌ {display_name} NOT found or error importing: {e}")
        return False
    except Exception as e:
        print(f"⚠️ {display_name} Error during import: {e}")
        return False

def main():
    print("--- Verifying Phase 3 Dependencies ---")
    
    # Core Phase 3
    tf_ok = check_import("tensorflow", "TensorFlow")
    st_ok = check_import("sentence_transformers", "Sentence Transformers")
    chroma_ok = check_import("chromadb", "ChromaDB")
    
    # Check if services can import them (simulating service logic)
    print("\n--- Verifying Service Imports ---")
    try:
        from services.deep_learning_service import DeepLearningService
        print(f"✅ DeepLearningService importable. Available: {DeepLearningService.is_available()}")
    except ImportError as e:
        print(f"❌ DeepLearningService import failed: {e}")
    except Exception as e:
        print(f"❌ DeepLearningService error: {e}")

    try:
        from services.rag_service import RAGService
        print(f"✅ RAGService importable. Available: {RAGService.is_available()}")
    except ImportError as e:
        print(f"❌ RAGService import failed: {e}")
    except Exception as e:
        print(f"❌ RAGService error: {e}")

    if tf_ok and st_ok and chroma_ok:
        print("\n🎉 All Phase 3 dependencies verified successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Some dependencies failed to load.")
        sys.exit(1)

if __name__ == "__main__":
    main()
