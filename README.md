# CDPM-Align: Multi-Scale Guidance-Aligned Diffusion Pretraining

This is the academic project page for the MICCAI 2026 accepted paper:

**CDPM-Align: Multi-Scale Guidance-Aligned Diffusion Pretraining for Robust Few-Shot Anatomical Landmark Detection**

## Paper Details

- **Venue**: MICCAI 2026 (Accepted)
- **Authors**: Roberto Di Via, Irina Voiculescu, Francesca Odone, Vito Paolo Pastore
- **Affiliations**: MaLGa-DIBRIS, University of Genoa | Oxford University

## Links

- [Code (GitHub)](https://github.com/Malga-Vision/CDPM-Align)

## Abstract

Anatomical landmark detection is a fundamental task in medical image analysis supporting a wide range of diagnostic and interventional workflows. Although recent methods have achieved sub-millimetric localisation, accuracy alone is not sufficient for clinical deployment, requiring reliability and robustness in prediction.

In this work, we introduce CDPM-align, a multi-scale guidance-aligned conditional diffusion pre-training for anatomical landmark detection. Our experimental setup focuses on few-shot regimes (10 and 25 annotated images). Specifically, we employ three popular heterogeneous small-scale benchmark datasets for representation learning via conditional generative pre-training.

Our results confirm that generative pre-training enables the model to learn robust representations. This improves both accuracy and uncertainty on the downstream tasks, advancing towards safe and efficient clinical deployment.

## Key Results

- **State-of-the-art few-shot performance**: Best MRE in 5/6 dataset-budget settings
- **Sub-millimetre ERE**: At 25-shot, achieves ERE below 1mm on ISBI2015 (0.95mm) and DHA (0.97mm)
- **+22% improvement** on ISBI2015 10-shot (2.11 vs 2.70 mm)
- **+42% improvement** on DHA 10-shot (2.51 vs 4.34 mm)
- **Data-efficient**: Pretrained on only 988 images, matches or surpasses models trained on 112k NIH radiographs

## Method

We propose CDPM-align, a conditional diffusion pretraining framework with multi-scale guidance alignment. The method consists of:

1. **Conditional Diffusion Probabilistic Model (CDPM)**: Training a class-conditional diffusion model with classifier-free guidance on small-scale heterogeneous X-ray datasets

2. **Multi-scale Alignment**: Enforcing directional consistency of the guidance signal across independently sampled diffusion timesteps and UNet hierarchy levels

3. **Downstream Fine-tuning**: End-to-end fine-tuning of the pretrained backbone for anatomical landmark detection with pixel-wise classification

## Datasets

- **Shenzhen**: 279 chest radiographs, 6 landmarks
- **ISBI2015**: 400 lateral cephalograms, 19 landmarks  
- **Digital Hand Atlas (DHA)**: 910 hand radiographs, 37 landmarks

## Website

This page is built using the [Academic Project Page Template](https://github.com/anonymity99/academic-page-template) and is hosted on GitHub Pages.

## License

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.
