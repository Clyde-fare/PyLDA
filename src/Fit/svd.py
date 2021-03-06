#!/usr/bin/env python

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from numpy import *
from numpy.linalg import *
from scipy.optimize import differential_evolution, minimize
from scipy.linalg import *
from scipy.special import *
from random import *
from matplotlib.widgets import Slider
from discreteslider import DiscreteSlider

class SVD(object):
    def __init__(self, data):
	self.updateData(data)
        
    def updateData(self, data):
        self.U, self.S, self.Vt = data.get_SVD()
	self.Svals = self.S
        self.S = diag(self.S)
        self.wLSV = self.U.dot(self.S)
        self.T = data.get_T()
	self.wls = data.get_wls()
	self.irforder, self.FWHM, self.munot, self.lamnot = data.get_IRF()
        self.FWHM_mod = self.FWHM/(2*sqrt(log(2)))

    def display(self):
        fig = plt.figure()
        fig.canvas.set_window_title('Singular Values')
	ax = fig.add_subplot(121)
        ax.plot(range(1,len(self.Svals)+1), self.Svals, 'o-')
	ax2 = fig.add_subplot(122)
	plt.subplots_adjust(left=0.25, bottom=0.25)
        ax2.plot(self.T, self.wLSV[:,0], 'bo-', label='wLSV 1')
        plt.xscale('log')
        plt.legend(loc=0, frameon=False)
	axS = plt.axes([0.25, 0.1, 0.65, 0.03])
        S = Slider(axS, 'wLSV', 1, len(self.wLSV[0]), valinit=1, valfmt='%0.0f')
        def update(val):
            n = int(S.val)
	    ax2.clear()
	    ax2.plot(self.T, self.wLSV[:,n-1], 'bo-', label='wLSV %d'%n)
	    ax2.set_xscale('log')
	    ax2.legend(loc=0, frameon=False)
	    plt.draw()
        S.on_changed(update)

    def _genD(self, taus, T):
        D = np.zeros([len(T), len(taus)])
        for i in range(len(D)):
            for j in range(len(D[i])):
                t = T[i]
                tau = taus[j]
                #One = 0.5*(exp(-t/tau)*exp((self.munot + (self.FWHM_mod**2/(2*tau)))/tau))
                #Two = 1 + erf((t-(self.munot+(self.FWHM_mod**2/tau)))/(sqrt(2)*self.FWHM_mod))
                #D[i, j] = One*Two
                D[i, j] = exp(-t/tau)
        return D

    def _getDAS(self, D, Y, alpha):
	if alpha != 0:
	    D_aug = np.concatenate((D, alpha**(0.5)*np.identity(len(D[0]))))
	    Y_aug = np.concatenate((Y, np.zeros([len(D[0]), len(Y[0])])))
	else:
	    D_aug = D
	    Y_aug = Y
        Q, R = np.linalg.qr(D_aug)
        Qt = np.transpose(Q)
        DAS = np.zeros([len(D_aug[0]),len(Y_aug[0])])
        QtY = Qt.dot(Y_aug)
        
        DAS[-1, :] = QtY[-1, :]/R[-1, -1]
        for i in range(len(DAS)-2, -1, -1):
            s = 0
            for k in range(i+1, len(DAS)):
                s += R[i, k]*DAS[k, :]
            DAS[i, :] = (QtY[i, :] - s)/R[i, i]
        return DAS

    def _min(self, taus, Y, T, alpha):
        D = self._genD(taus, T)
        DAS = self._getDAS(D, Y, alpha)
        res = sum((Y - D.dot(DAS))**2)
        return res

    def _GA(self, x0, Y, T, alpha, B):
        #result = differential_evolution(self._min, bounds=B, args=(Y, T, alpha), tol=0.00001, popsize=100, polish=True))
	result = minimize(self._min, x0, args=(Y, T, alpha), bounds=B)
        taus = result.x
        D = self._genD(taus, T)
        DAS = self._getDAS(D, Y, alpha)
	print taus
        return taus, DAS, D.dot(DAS)

    def Global(self, wLSVs, x0, B, alpha):
	wLSVs = map(int, wLSVs.split(' '))
	if wLSVs == None:
	    wLSV_fit = self.wLSV[:, :len(B)]
	elif len(wLSVs) == 1:
	    wLSV_fit = self.wLSV[:, :wLSVs[0]]
	else:
	    wLSV_fit = np.zeros([len(self.T), len(wLSVs)])
	    for j in range(len(wLSVs)):
		wLSV_fit[:, j] = self.wLSV[:, wLSVs[j]-1]

	taus, DAS, SpecFit = self._GA(x0, wLSV_fit, self.T, alpha, B)
	self._plot_res(wLSV_fit, wLSVs, taus, DAS, SpecFit, self.T)
	return taus

    def _plot_res(self, wLSV_fit, wLSVs, taus, DAS, SpecFit, T):
	if len(wLSVs) == 1:
	    wLSVs = range(1, wLSVs[0]+1)
        fig = plt.figure()
	fig.canvas.set_window_title('GA Fits')
	plt.subplots_adjust(left=0.25, bottom=0.25)
	ax = fig.add_subplot(121)
	for i in range(len(DAS)):
	    ax.plot(range(1, len(DAS[0])+1), DAS[i, :], label="%.3f"%taus[i])
	ax.legend(loc=0, frameon=False)

	ax2 = fig.add_subplot(122)
        ax2.plot(T, wLSV_fit[:,0], 'bo-', label='wLSV 1')
        ax2.plot(T, SpecFit[:,0], 'r', label='Fit')
        ax2.set_xscale('symlog', linthreshy=1)
        ax2.legend(loc=0, frameon=False)
	axS = plt.axes([0.25, 0.1, 0.65, 0.03])
        S = DiscreteSlider(axS, 'wLSV', 1, len(taus)+1, valinit=1, valfmt='%0.0f', increment=1)
        def update(val):
            n = int(S.val)
	    ax2.clear()
	    ax2.plot(T, wLSV_fit[:,n-1], 'bo-', label='wLSV %d'%wLSVs[n-1])
	    ax2.plot(T, SpecFit[:,n-1], 'r', label='Fit')
	    ax2.set_xscale('symlog', linthreshy=1)
	    ax2.legend(loc=0, frameon=False)
	    plt.draw()
        S.on_changed(update)
	plt.draw()

        
        
