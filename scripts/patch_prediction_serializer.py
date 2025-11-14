#!/usr/bin/env python3
"""
Patch PredictionSerializer to add AIV prefix to model_version.

This script modifies the Label Studio prediction serializer to automatically
add "AIV " prefix to model_version when sending predictions to the frontend.
"""

import os

SERIALIZER_PATH = "/label-studio/label_studio/tasks/serializers.py"

def patch_prediction_serializer():
    """Add to_representation override to PredictionSerializer."""

    if not os.path.exists(SERIALIZER_PATH):
        print(f"[AIV PATCH] ❌ File not found: {SERIALIZER_PATH}")
        return False

    with open(SERIALIZER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already patched
    if "AIV prefix patch" in content:
        print("[AIV PATCH] ⚠️  Already patched, skipping")
        return True

    # Find the PredictionSerializer class and add to_representation method
    # We'll add it right after the class definition and fields

    # Find the insertion point - after the Meta class in PredictionSerializer
    pattern = "class PredictionSerializer(ModelSerializer):"

    if pattern not in content:
        print(f"[AIV PATCH] ❌ PredictionSerializer class not found")
        return False

    # Find the end of Meta class within PredictionSerializer
    # We'll insert our method after the Meta class

    # Split at PredictionSerializer class
    parts = content.split(pattern)
    if len(parts) != 2:
        print(f"[AIV PATCH] ❌ Unexpected file structure")
        return False

    before_class = parts[0]
    after_class_start = parts[1]

    # Find a good insertion point - after the model_version field definition
    # Look for the next method or end of field definitions
    lines = after_class_start.split('\n')

    insert_index = 0
    found_model_version = False
    indent_level = 0

    for i, line in enumerate(lines):
        # Track if we found model_version field
        if 'model_version = serializers' in line:
            found_model_version = True
            # Find the indent level
            indent_level = len(line) - len(line.lstrip())

        # After finding model_version, look for the next field or method at same indent
        if found_model_version and i > 0:
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            # If we hit a line with same or less indentation that starts with def or class
            if current_indent <= indent_level and (stripped.startswith('def ') or stripped.startswith('class ')):
                insert_index = i
                break

            # Or if we hit another field definition at same level
            if current_indent == indent_level and '=' in stripped and not stripped.startswith('#'):
                continue

    if not found_model_version:
        print(f"[AIV PATCH] ❌ model_version field not found")
        return False

    if insert_index == 0:
        # If we didn't find a good spot, try to find Meta class
        for i, line in enumerate(lines):
            if 'class Meta:' in line:
                # Find the end of Meta class
                for j in range(i+1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(' ' * (len(lines[i]) - len(lines[i].lstrip()) + 4)):
                        insert_index = j
                        break
                break

    # Prepare the method to insert
    method_code = '''
    def to_representation(self, instance):
        """Override to add AIV prefix to model_version for frontend display."""
        # AIV prefix patch: add "AIV " to model_version
        ret = super().to_representation(instance)

        # Add AIV prefix only if model_version exists and is not empty
        if ret.get('model_version'):
            ret['model_version'] = f"AIV {ret['model_version']}"

        return ret
'''

    # Insert the method
    lines.insert(insert_index, method_code)

    # Reconstruct the content
    new_content = before_class + pattern + '\n'.join(lines)

    # Write back
    with open(SERIALIZER_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("[AIV PATCH] ✅ Successfully patched PredictionSerializer")
    print("[AIV PATCH]    Added to_representation method to add AIV prefix to model_version")

    return True


if __name__ == '__main__':
    success = patch_prediction_serializer()
    exit(0 if success else 1)
