# Revised concepts v2 — branches, moving filters and multiple layers

[한국어](README.ko.md)

The four-scene limit is removed. Backprop has 10 stages, CNN has 9 explanation chapters and 82 scan positions, and Dropout has 8 chapters. Watch each storyboard, then open the full-size stills to read at your own pace. **Explanation and difficulty review; final films have not started.**

## 1. Backpropagation: AB + CDE

Five variables feed AB+CDE. The loss signal travels backward through the addition and both product branches to all five gradients, followed by a real update.

![Backpropagation: AB + CDE — animated concept](v2/backprop.en.gif)

<details><summary>Read full-size stills at your own pace</summary>

**1. Five inputs and two branches**

![Five inputs and two branches](v2/backprop.en.1.png)

**2. Compute AB and CD**

![Compute AB and CD](v2/backprop.en.2.png)

**3. Finish CDE, output and loss**

![Finish CDE, output and loss](v2/backprop.en.3.png)

**4. Start backward**

![Start backward](v2/backprop.en.4.png)

**5. Send to both branches at addition**

![Send to both branches at addition](v2/backprop.en.5.png)

**6. Back through AB**

![Back through AB](v2/backprop.en.6.png)

**7. Back through CDE**

![Back through CDE](v2/backprop.en.7.png)

**8. Back through CD**

![Back through CD](v2/backprop.en.8.png)

**9. All five gradients**

![All five gradients](v2/backprop.en.9.png)

**10. One update**

![One update](v2/backprop.en.10.png)

</details>

## 2. CNN: moving windows and layers

A moving 3×3 filter fills the output map cell by cell. A second filter, stride 2, stacked channels, the next convolution layer and final scores follow. The first CNN layer is then unrolled into the exact same matrix calculation before comparing parameter counts. **This compares structures, not equal measured accuracy.**

![CNN: moving windows and layers — animated concept](v2/cnn.en.gif)

<details><summary>Read full-size stills at your own pace</summary>

**1. Calculate one patch**

![Calculate one patch](v2/cnn.en.1.png)

**2. Scan the first filter**

![Scan the first filter](v2/cnn.en.2.png)

**3. Scan the second filter**

![Scan the second filter](v2/cnn.en.3.png)

**4. Compare stride 2**

![Compare stride 2](v2/cnn.en.4.png)

**5. Stack feature channels**

![Stack feature channels](v2/cnn.en.5.png)

**6. Combine channels in the next layer**

![Combine channels in the next layer](v2/cnn.en.6.png)

**7. Compute final scores**

![Compute final scores](v2/cnn.en.7.png)

**8. Unroll as a matrix**

![Unroll as a matrix](v2/cnn.en.8.png)

**9. Compare independent parameter counts**

![Compare independent parameter counts](v2/cnn.en.9.png)

</details>

## 3. Dropout: 5 → 10 → 5 → 2

In a5→10→5→2 network, both hidden layers change their participating units and paths. Follow the surviving paths, switch masks, then restore all units at prediction time.

![Dropout: 5 → 10 → 5 → 2 — animated concept](v2/dropout.en.gif)

<details><summary>Read full-size stills at your own pace</summary>

**1. The full network**

![The full network](v2/dropout.en.1.png)

**2. Hide some first-layer units**

![Hide some first-layer units](v2/dropout.en.2.png)

**3. Hide some next-layer units**

![Hide some next-layer units](v2/dropout.en.3.png)

**4. Follow participating paths**

![Follow participating paths](v2/dropout.en.4.png)

**5. Change the mask**

![Change the mask](v2/dropout.en.5.png)

**6. Change both layers again**

![Change both layers again](v2/dropout.en.6.png)

**7. Prediction with all units**

![Prediction with all units](v2/dropout.en.7.png)

**8. Why vary the team?**

![Why vary the team?](v2/dropout.en.8.png)

</details>

## Review this revision

Can you follow the backward branches, the moving CNN filters and layered/matrix views, and the changing dropout subnetworks? For each topic: approve, revise the explanation, or adjust the difficulty. Only approved topics move to refinement.

[계산 조건·원문 / source contract](BRIEF.md) · [검증 / verification](v2/verification.json)

Adam, Attention and ResNet remain the three finished lessons. [Live collection](https://chocoemong17.github.io/chainbench/papers/)
