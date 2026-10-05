# Revised concepts v3 — branches, moving filters and multiple layers

[한국어](README.ko.md)

Updated from your v2 feedback: repeated updates toward the target, numbers in colored CNN cells, and fewer Dropout nodes. Backprop has 12 stages, CNN has 9 explanation chapters and 82 scan positions, and Dropout has 8 chapters. Watch each storyboard, then open the full-size stills to read at your own pace. **Explanation and difficulty review; final films have not started.**

## 1. Backpropagation: AB + CDE

Five variables feed AB+CDE. The loss signal travels backward through the addition and both product branches to all five gradients, followed by six real updates. After the detailed first update, fast forward/backward/update cycles show the prediction approaching target 4; a final chart collects the progress. The repeated cycles now take 13 seconds and the final chart stays for 6 seconds, for **59 seconds** in total.

![Backpropagation: AB + CDE — animated concept](v3/backprop.en.gif)

<details><summary>Read full-size stills at your own pace</summary>

**1. Five inputs and two branches**

![Five inputs and two branches](v3/backprop.en.1.png)

**2. Compute AB and CD**

![Compute AB and CD](v3/backprop.en.2.png)

**3. Finish CDE, output and loss**

![Finish CDE, output and loss](v3/backprop.en.3.png)

**4. Start backward**

![Start backward](v3/backprop.en.4.png)

**5. Send to both branches at addition**

![Send to both branches at addition](v3/backprop.en.5.png)

**6. Back through AB**

![Back through AB](v3/backprop.en.6.png)

**7. Back through CDE**

![Back through CDE](v3/backprop.en.7.png)

**8. Back through CD**

![Back through CD](v3/backprop.en.8.png)

**9. All five gradients**

![All five gradients](v3/backprop.en.9.png)

**10. First update: closer to the target**

![One update](v3/backprop.en.10.png)

**11. Repeat forward → backward → update**

![Second update; the animation repeats through update 6](v3/backprop.en.11.png)

**12. Progress toward target 4**

![All six updates approaching the target](v3/backprop.en.12.png)

</details>

## 2. CNN: moving windows and layers

A moving 3×3 filter fills the output map cell by cell. Colored input cells show 1; computed nonzero output values remain visible. Zero cells stay blank. A second filter, stride 2, stacked channels, the next convolution layer and final scores follow. The first CNN layer is then unrolled into the exact same matrix calculation before comparing parameter counts. **This compares structures, not equal measured accuracy.**

![CNN: moving windows and layers — animated concept](v3/cnn.en.gif)

<details><summary>Read full-size stills at your own pace</summary>

**1. Calculate one patch**

![Calculate one patch](v3/cnn.en.1.png)

**2. Scan the first filter**

![Scan the first filter](v3/cnn.en.2.png)

**3. Scan the second filter**

![Scan the second filter](v3/cnn.en.3.png)

**4. Compare stride 2**

![Compare stride 2](v3/cnn.en.4.png)

**5. Stack feature channels**

![Stack feature channels](v3/cnn.en.5.png)

**6. Combine channels in the next layer**

![Combine channels in the next layer](v3/cnn.en.6.png)

**7. Compute final scores**

![Compute final scores](v3/cnn.en.7.png)

**8. Unroll as a matrix**

![Unroll as a matrix](v3/cnn.en.8.png)

**9. Compare independent parameter counts**

![Compare independent parameter counts](v3/cnn.en.9.png)

</details>

## 3. Dropout: 3 → 5 → 5 → 2

In a3→5→5→2 network, both hidden layers change their participating units and paths. Follow the surviving paths, switch masks, then restore all units at prediction time.

![Dropout: 3 → 5 → 5 → 2 — animated concept](v3/dropout.en.gif)

<details><summary>Read full-size stills at your own pace</summary>

**1. The full network**

![The full network](v3/dropout.en.1.png)

**2. Hide some first-layer units**

![Hide some first-layer units](v3/dropout.en.2.png)

**3. Hide some next-layer units**

![Hide some next-layer units](v3/dropout.en.3.png)

**4. Follow participating paths**

![Follow participating paths](v3/dropout.en.4.png)

**5. Change the mask**

![Change the mask](v3/dropout.en.5.png)

**6. Change both layers again**

![Change both layers again](v3/dropout.en.6.png)

**7. Prediction with all units**

![Prediction with all units](v3/dropout.en.7.png)

**8. Why vary the team?**

![Why vary the team?](v3/dropout.en.8.png)

</details>

## Review this revision

Does repeated backprop visibly approach the target? Do the CNN numbers clarify the scan? Is the smaller Dropout network easier to follow? For each topic: ready to refine, revise the explanation, or adjust the difficulty. Only approved topics move to refinement.

[계산 조건·원문 / source contract](BRIEF.md) · [검증 / verification](v3/verification.json)

Adam, Attention and ResNet remain the three finished lessons. [Live collection](https://chocoemong17.github.io/chainbench/papers/)
