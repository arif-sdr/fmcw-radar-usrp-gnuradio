# FMCW Radar using GNU Radio and USRP

This project implements a simple FMCW radar in GNU Radio using USRP for presence detection and coarse range estimation.

## Overview

The radar transmits a chirp signal, receives the reflected signal, and processes the beat frequency to detect objects.
The system uses FFT-based spectrum analysis to estimate target presence and approximate distance.

## Files

- `radar_simple.grc` - Main GNU Radio flowgraph

## Main parameters

- Center frequency: 2.45 GHz
- Chirp bandwidth: 20 MHz
- Chirp period: 1 ms
- FFT size: 1024
- TX gain: 80
- RX gain: 35

## Features

- FMCW chirp generation
- USRP-based transmission and reception
- Beat signal extraction
- FFT-based spectrum display
- Presence detection
- Coarse range estimation

## Tools and Hardware

- GNU Radio
- USRP
- Python
- Linux

## Notes

This project is intended for SDR-based radar experimentation and testing.
