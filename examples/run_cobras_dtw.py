import os

import numpy as np
from dtaidistance import dtw
from cobras_ts.cobras_dtw import COBRAS_DTW
from cobras_ts.querier.labelquerier import LabelQuerier
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import DBA as dba
from matplotlib.patches import Ellipse
import datetime as dt


ucr_path = '/Users/ary/Desktop/Thesis/UCR_TS_Archive_2015'
dataset = 'ECG200'
#dataset = 'Beef'
budget = 100
alpha = 0.5
window = 3
iteration = 1
cluster_idx = 0



# load the data
data = np.loadtxt(os.path.join(ucr_path,dataset,dataset + '_TEST'), delimiter=',')
series = data[:,1:]
labels = data[:,0]

start = 0
end = series.shape[1]

print("series cnt = " + str(series.shape[0]))
print("series shape = " + str(series.shape[1]))

# construct the affinity matrix
dt1 = dt.datetime.now()
dists = dtw.distance_matrix(series, window=int(0.01 * window * series.shape[1]))
dt2 = dt.datetime.now()
print("distance matrix use time " + str((dt2 - dt1).seconds))
dists[dists == np.inf] = 0
dists = dists + dists.T - np.diag(np.diag(dists))
affinities = np.exp(-dists * alpha)

# initialise cobras_dtw with the precomputed affinities
clusterer = COBRAS_DTW(affinities, LabelQuerier(labels), budget)

clustering, intermediate_clusterings, runtimes, ml, cl = clusterer.cluster()
dt3 = dt.datetime.now()
print("cluster use time " + str((dt3 - dt2).seconds))

print("there are " + str(len(clustering.clusters)) + " clusters")


fig = plt.figure()
ax1 = fig.add_subplot(231)                              #DBA
ax2 = fig.add_subplot(232, sharex = ax1, sharey = ax1)  #adjusted dots
ax3 = fig.add_subplot(233,  sharex = ax1, sharey = ax1) #eclipse
ax4 = fig.add_subplot(234, sharex = ax1)  #dtw_vertical
ax5 = fig.add_subplot(235, sharex = ax1, sharey = ax4)  #vertical
ax6 = fig.add_subplot(236, sharex = ax1, sharey = ax4) #dtw_horizontal

ax_overall = [ax1, ax2, ax3]
ax_statistic = [ax4, ax5, ax6]
axs = ax_overall + ax_statistic

#axis color
for ax in axs:
    ax.spines['bottom'].set_color('blue')
    ax.spines['bottom'].set_linewidth(2)
    ax.spines['left'].set_linewidth(2)
    ax.set_xlabel("time")

for ax in ax_overall:
    ax.spines['left'].set_color('pink')
for ax in ax_statistic:
    ax.spines['left'].set_color('yellow')

x = np.arange(0, series.shape[1])

#y_label
ax1.set_ylabel("DBA", color = "purple")
ax2.set_ylabel("Instances", color = "blue")
ax3.set_ylabel("DBA with Deviations", color = "blue")
ax6.set_ylabel("Wrapped Horizontal Deviation", color = "green")
ax4.set_ylabel("Wrapped Vertical Deviation", color = "red")
ax5.set_ylabel("Standard Deviation", color = "gray")


def findAllIndicesOfOneCluster(cluster_idx):
    superinstances = clustering.clusters[cluster_idx].super_instances
    indices_of_current_cluster = []
    for superinstance in superinstances:
        indices_of_current_cluster += superinstance.indices
    return indices_of_current_cluster

def findAllSeriesWithIndices(indices):
    target_series = list(map(lambda idx: series[idx], indices))
    return target_series

def getColorIter(size):
    color_arr = cm.rainbow(np.linspace(0, 1, size))
    colors = iter(color_arr)
    return colors


def plotDBA(plt, series_mean, range = None):
    if (range == None):
        plt.plot(x, series_mean, color='purple')
    elif (range[0] + 1 == range[1]):
        plt.scatter(x[range[0]], series_mean[range[0]], color = 'purple')
    else:
        plt.plot(x[range[0]: range[1]], series_mean[range[0]: range[1]], color = 'purple')

def plotEclipseAroundDBA(ax1, series_mean, series_dtw_horiz_var, series_dtw_vertic_var, span_tuple):
    color_type_num = 10
    color_arr = cm.rainbow(np.linspace(0, 1, color_type_num))
    ells = [Ellipse(xy=(i, series_mean[i]),
                    width=series_dtw_horiz_var[i], height=series_dtw_vertic_var[i], color=color_arr[i%color_type_num])
            for i in np.arange(span_tuple[0], span_tuple[1])
            ]
    for e in ells:
        ax1.add_artist(e)

def plotDeviations(plt, values, color, range = None) :
    if (range == None):
        plt.plot(x, values, color=color)
    elif (range[0] + 1 == range[1]):
        plt.scatter(x[range[0]], values[range[0]], color=color)
    else:
        plt.plot(x[range[0]: range[1]], values[range[0]: range[1]], color=color)

    # adjusted_series_weight_mat ?????????????????????
    # series_mapping_mat         ???????????????index
    # ??????range???[ a, b )
def plotAdjustedSeries(plt, series_mapping_mat, adjusted_series_weight_mat, range, series):
    plt.set_title("count = " + str(len(series)))
    colors = getColorIter(series_mapping_mat.shape[0])
    for series_index in np.arange(0, series_mapping_mat.shape[0]):
        s1, e1 = dba.getStartAndEndMapping(series_mapping_mat, adjusted_series_weight_mat, series_index, range[1] - 1)
        s2, e2 = dba.getStartAndEndMapping(series_mapping_mat, adjusted_series_weight_mat, series_index, range[0])

        x = np.arange(s2, e1)
        y = list(map(lambda  x: series[series_index][x], x))
        if len(x) == 1:
            plt.scatter(x, y, color=next(colors))
        else:
            plt.plot(x, y, color=next(colors))
        expected_range = np.arange(range[0], range[1])
        non_plotted_range = [item for item in expected_range if item not in x]
        for non_plotted_dot in non_plotted_range:
            plt.scatter(non_plotted_dot, series[series_index][non_plotted_dot], color = 'black')


def plotSelectedSpan(span_tuple, cluster_idx):
    cur_series = findAllSeriesWithIndices(findAllIndicesOfOneCluster(cluster_idx))
    dt4 = dt.datetime.now()

    series_mean, series_dtw_horiz_var, series_dtw_vertic_var, series_vertic_var, adjusted_series_mat, series_mapping_mat, adjusted_series_weight_mat, series_dtw_special_vertic_var = dba.performDBA(cur_series, iteration)
    dt5 = dt.datetime.now()
    print("getting DBA use time " + str((dt5 - dt4).seconds))

    plotDBA(ax1, series_mean, span_tuple)
    #plotRawAverage(ax1, cur_series)
    plotAdjustedSeries(ax2, series_mapping_mat, adjusted_series_weight_mat, span_tuple, cur_series)
    plotStatisticsCurves(series_dtw_horiz_var, series_dtw_vertic_var, series_vertic_var, series_dtw_special_vertic_var, span_tuple)
    plotDBA(ax3, series_mean, span_tuple)
    plotEclipseAroundDBA(ax3, series_mean, series_dtw_horiz_var, series_dtw_vertic_var, span_tuple)


def plotStatisticsCurves(series_dtw_horiz_var, series_dtw_vertic_var, series_vertic_var, series_dtw_special_vertic_var, span_tuple = None):
    plotDeviations(ax4, series_dtw_vertic_var, 'red', span_tuple)
    plotDeviations(ax5, series_vertic_var, 'grey', span_tuple)
    plotDeviations(ax6, series_dtw_horiz_var, 'green', span_tuple)
    # plotStatisticsCurve(ax6, series_dtw_special_vertic_var, 'purple', span_tuple)


def main():
    # print(metrics.adjusted_rand_score(clustering.construct_cluster_labeling(),labels))

    # special_indices = findSpecialIndices()
    # print(special_indices)
    # plotSpecialCaseOverall(special_indices)
    # plotSpecialSelectedSpan((85,95), special_indices)

    plotSelectedSpan((start, end), 1)
    # plotSelectedSpan((start, end), 1)
    plt.show()
if __name__ == '__main__':
    main()

#experimental
def plotDeviationAroundDBA(ax1, series_mean, series_vertic_var, span_tuple = None):
    lower = series_mean - series_vertic_var
    upper = series_mean + series_vertic_var
    real_x = x
    if span_tuple != None:
        real_x = x[span_tuple[0]: span_tuple[1]]
        lower = lower[span_tuple[0]: span_tuple[1]]
        upper = upper[span_tuple[0]: span_tuple[1]]
    ax1.fill_between(real_x, lower, upper, alpha=0.1)

#experimental
def plotRawAverage(plt, cur_series):
    avg = np.divide(np.sum(cur_series, 0), len(cur_series))
    plt.plot(x, avg, color='purple')

#experimental
def plotMultiCurves(plt, indices, title, showLabel=False):
    plt.set_title(title + ' count=' + str(len(indices)))
    colors = getColorIter(len(indices))
    indices.sort()
    for index in indices:
        cur_color = next(colors)
        y = series[index]
        if showLabel == True:
            plt.plot(x, y, color=cur_color, label="index=" + str(index))
        else:
            plt.plot(x, y, color=cur_color)
    if showLabel == True & len(indices) < 15:
        plt.legend(loc = 9)

