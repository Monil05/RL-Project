import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Hashes recorded before the API and web application were added.
PROTECTED = {
    "agents/q_learning.py": "690a2b13ba0972538fdf7d6b5f8274cf34137c90ab1877317ae8d29416ac78d2",
    "agents/sarsa.py": "7f43596a666195d5ae1c0cc2f54ccb83dcfbe4b8b3bda5a011f40d191eaf70e3",
    "agents/tabular_agent.py": "6b6f04af8edc8a9e71f76e1acd772bec21fbb9e156444d3712327dbd3c643c92",
    "agents/__init__.py": "59d0e3269b10cca95a6a35ed48afa69ab25feef1fe03c2bdb7ba940fc2d4725b",
    "environment/traffic_environment.py": "bd9de5d92bb08ee0665faa2b92e388cbe1499a50125cb9d0c037ab6ec3a00b1d",
    "environment/signal_controller.py": "c8f4ff0579ddd5b5490847bc39180b1e17ec3381c866959c6685874586d3f45f",
    "environment/gym_env.py": "faaa2d73e11132cf1d06044c0c3b4c50a1aad396721b6484e3585b9f40f34720",
    "environment/__init__.py": "f48f494bd004f908d5b8a33a1ab0845b55ae7fa03305d8e17cc054a14a1e848c",
    "baseline.py": "e93694ad2a6fcfdbf192cf6e9c7565b9a234aceabb48d0980f82a9ffd559d891",
    "training/train.py": "c8cb11228dc963864434119dc438b711962036bc1f4a897c415befefe07a491b",
    "training/__init__.py": "a7f81dd03f04ee5480535fc4fe33a69ad89718c595c17a13f1ad7687467fed24",
    "evaluation/evaluate.py": "6efc3d6300061260db4388d0be8e64aac1f6f6ceec4a3f349596b15818224a63",
    "evaluation/__init__.py": "1bf1ef8d5675c8800ccdba5978536e1a42078df8fe6f0469ebf2893eb0b144d1",
    "config.py": "6c98c3747cca927754a1ff1023a77a8cb56a476bf71a23bfb8ef172dd9f26734",
    "experiments.py": "6dc01dd1c04db2f4e97d7b57552500732f4f81ecb0dffb28539c39cd1e6af713",
    "main.py": "67813547534cfcf486517d8d450f91c73b533f67f81ccde3d5cc59205cbce0bc",
    "results/experiment_results.csv": "451cb1d609b7f5e08d8c2b6dd5d260cf50da86516eeedc994b7cf60148c42789",
    "results/experiment_summary.csv": "13d482737a0d4942bf942fba84f3e491c869307cdb8be9cd975fca037ca44bd2",
}


def test_protected_rl_files_are_unchanged():
    changed = []
    for relative, digest in PROTECTED.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != digest:
            changed.append(relative)
    assert changed == []
