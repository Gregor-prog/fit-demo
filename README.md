One fit at noise 0.1
  true  : (2.0, 3.0, 4.0)
  fitted: [1.99 2.96 4.06]   uncertainty: [0.01 0.05 0.11]
  residual rms: 0.099 (should be close to the noise level, 0.1)

Noise test: spread of fitted values over repeated fits
true values: {'gain': 2.0, 'delay': 3.0, 'tau': 4.0}
 sigma  fits |    gain mean±std   delay mean±std     tau mean±std | relative spread (std/true)
  0.10   100 |    2.00±0.01       3.00±0.05       4.00±0.12    | gain=   1%  delay=   2%  tau=   3%
  0.50   100 |    2.00±0.07       3.03±0.27       3.97±0.62    | gain=   4%  delay=   9%  tau=  15%
  1.00   100 |    2.05±0.16       2.95±0.62       4.38±1.48    | gain=   8%  delay=  21%  tau=  37%
  2.00   100 |    2.14±0.43       2.67±1.34       5.24±3.79    | gain=  22%  delay=  45%  tau=  95%

Saved: fit_examples.png, noise_spread.png
