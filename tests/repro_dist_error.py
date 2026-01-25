from src.common.types import StatTypeRegistry

def test_distribution_ignore_unconfigured_stats():
    # Create distribution WITHOUT 'samples' in statistics
    dist = StatTypeRegistry.create(
        "distribution", 
        minimum=0, 
        maximum=10, 
        statistics=[] # No stats requested
    )
    
    # Input content contains 'samples' (simulating parser output)
    content = {
        "underflows": [],
        "overflows": [],
        **{str(i): [] for i in range(11)}, # Populate 0..10
        "samples": ["100"] # This caused the crash
    }
    
    # Should NOT raise TypeError
    try:
        dist.content = content
    except TypeError as e:
        print(f"FAILED: Raised TypeError for unconfigured stat: {e}")
        exit(1)
    except Exception as e:
        print(f"FAILED: Raised unexpected exception: {e}")
        exit(1)

if __name__ == "__main__":
    test_distribution_ignore_unconfigured_stats()
    print("Test passed!")
