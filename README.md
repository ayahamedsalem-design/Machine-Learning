# Machine Learning Project
## Session #2 Assignment
Embedding a PDF file using Multi-Types RAGs
- Basic RAG
- Hierarchical (Parent-Child) RAG
- Hybrid RAG

Model: nvidia/nemotron-3.5-embed-1b:free

Storing the embeddings using ChromaDB

## How to Run
1. Run individual RAG using its Main method
2. Run the UI to run all RAGs
> streamlit run app.py

You can check the Terminal Log for full details

# Result

## Basic RAG Result
```
============================================================
Model Response:
============================================================
The main architecture of the Neural Network is described in the paper as follows:

1. The network has 8 layers.
2. The layers are:
   - 5 convolutional layers
   - 3 fully-connected (or dense) layers
3. The convolutional layers are:
   - The first 5 convolutional layers are connected to each other without any intervening pooling or normalization layers.
   - The second convolutional layer takes as input the (response-normalized and pooled) output of the first convolutional layer and filters it with 256 kernels of size 5× 5× 48.
   - The third, fourth, and fifth convolutional layers are connected to one another without any intervening pooling or normalization layers.
   - The third convolutional layer has 384 kernels of size 3× 3× 256 connected to the (normalized, pooled) outputs of the second convolutional layer.
   - The fourth convolutional layer has 384 kernels of size 3× 3× 192.
   - The fifth convolutional layer has 256 kernels of size 3× 3× 192.
4. The fully-connected layers have 4096 neurons each.

Therefore, the main architecture of the Neural Network is an 8-layer neural network with 5 convolutional layers and 3 fully-connected layers.```