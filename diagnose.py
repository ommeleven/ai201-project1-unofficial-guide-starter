print("step 1: basic python ok")
import numpy as np
print("step 2: numpy ok")
import torch
print("step 3: torch ok")
from sentence_transformers import SentenceTransformer
print("step 4: sentence_transformers import ok")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("step 5: model loaded ok")
result = model.encode(["hello world"])
print("step 6: encode ok", result.shape)
