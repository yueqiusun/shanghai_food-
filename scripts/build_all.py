import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_icons_and_pwa
import gen_markdown_guide
import gen_webapp


def main():
    print("[1/3] Generating PWA icons, manifest & service worker...")
    gen_icons_and_pwa.main()
    print("[2/3] Generating docs/index.html Web App...")
    gen_webapp.main()
    print("[3/3] Generating shanghai_food_map.md guide...")
    gen_markdown_guide.main()
    print("All build steps completed successfully!")


if __name__ == "__main__":
    main()
