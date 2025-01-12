import time

from collections import deque
import imageio
from moviepy.video.io.VideoFileClip import VideoFileClip
from sklearn.externals import joblib

import utils
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import cv2

from skimage.feature import hog
from sklearn.preprocessing import StandardScaler
from sklearn.cross_validation import train_test_split
from sklearn.svm import LinearSVC
from scipy.ndimage.measurements import label

#CONSTANTS
VEHICLE_IMAGES = 'data/vehicles/**/*.png'
NON_VEHICLE_IMAGES = 'data/non-vehicles/**/*.png'

#load data
vehicle_data = utils.load_data(VEHICLE_IMAGES)
non_vehicle_data = utils.load_data(NON_VEHICLE_IMAGES)

print('loaded vehicle images')
print('loaded non vehicle images')

t = time.time()
vehicle_features = utils.extract_features(vehicle_data,
                                          color_space=utils.COLORSPACE,
                                          spatial_size=utils.SPATIAL_SIZE,
                                          hist_bins=utils.HIST_BINS,
                                          orient=utils.ORIENT,
                                          pix_per_cell=utils.PX_PER_CELL,
                                          cell_per_block=utils.CELL_PER_BLOCK,
                                          hog_channel=utils.HOG_CHANNEL,
                                          spatial_feat=utils.SPATIAL_FEATURES,
                                          hist_feat=utils.HIST_FEATURES,
                                          hog_feat=utils.HOG_FEATURES)

non_vehicle_features = utils.extract_features(non_vehicle_data,
                                          color_space=utils.COLORSPACE,
                                          spatial_size=utils.SPATIAL_SIZE,
                                          hist_bins=utils.HIST_BINS,
                                          orient=utils.ORIENT,
                                          pix_per_cell=utils.PX_PER_CELL,
                                          cell_per_block=utils.CELL_PER_BLOCK,
                                          hog_channel=utils.HOG_CHANNEL,
                                          spatial_feat=utils.SPATIAL_FEATURES,
                                          hist_feat=utils.HIST_FEATURES,
                                          hog_feat=utils.HOG_FEATURES)
t2 = time.time()
print(round(t2-t, 2), 'Seconds to extract HOG features...')

#get a feel for HOGs
# vehicle_data = utils.load_data(VEHICLE_IMAGES)
# v = plt.imread(vehicle_data[999])
# f,hi = utils.get_hog_features(v[:,:,0], utils.ORIENT, utils.PX_PER_CELL, utils.CELL_PER_BLOCK,vis=True, feature_vec=True)

# plt.figure(figsize=(10,5))
# plt.subplot(1, 2, 1)
# plt.imshow(v)
# plt.xlabel('Vehicle')
#
# plt.subplot(1, 2, 2)
# plt.imshow(hi)
# plt.xlabel('Vehicle HOG')
# plt.show(block=True)

# Create an array stack of feature vectors
X = np.vstack((vehicle_features, non_vehicle_features)).astype(np.float64)
# Fit a per-column scaler
X_scaler = StandardScaler().fit(X)
# Apply the scaler to X
scaled_X = X_scaler.transform(X)
# Define the labels vector
y = np.hstack((np.ones(len(vehicle_features)), np.zeros(len(non_vehicle_features))))

# Split up data into randomized training and test sets
rand_state = np.random.randint(0, 100)
X_train, X_test, y_train, y_test = train_test_split(
    scaled_X, y, test_size=0.2, random_state=rand_state)

# # Use a linear SVC
svc = LinearSVC(C=5)
# Check the training time for the SVC
t = time.time()
svc.fit(X_train, y_train)
t2 = time.time()
print(round(t2 - t, 2), 'Seconds to train SVC...')
# Check the score of the SVC
print('Test Accuracy of SVC = ', round(svc.score(X_test, y_test), 4))
# Check the prediction time for a single sample
t = time.time()
n_predict = 10
print('My SVC predicts: ', svc.predict(X_test[0:n_predict]))
print('For these', n_predict, 'labels: ', y_test[0:n_predict])
t2 = time.time()
print(round(t2 - t, 5), 'Seconds to predict', n_predict, 'labels with SVC')

#save svc - saves some training time
#joblib.dump(svc, 'svc.pkl')
#load model
# svc = joblib.load('svc.pkl')
# print('loading')

#test image
image = mpimg.imread('/home/pierro/Work/udacity/self-driving-car/p5/test_images/test1.jpg')
image = image.astype(np.float32)/255
draw_image = np.copy(image)

#sliding window implementation
windows_64 = utils.slide_window(image, x_start_stop=[None, None], y_start_stop=[375, 430],
                    xy_window=(64, 64), xy_overlap=(0.9, 0.9))

windows_128 = utils.slide_window(image, x_start_stop=[70, None], y_start_stop=[375, 560],
                    xy_window=(128, 128), xy_overlap=(0.9, 0.9))

windows = windows_64 + windows_128

#test sliding Windows
# sliding_windows = utils.draw_boxes(draw_image, windows, color=(0, 0, 255), thick=6)
# plt.imshow(sliding_windows)
# plt.xlabel('windows')
# plt.show(block=True)

print('processing video')
d = deque(maxlen=10)
def pipeline(video):
    video = video.astype(np.float32) / 255

    hot_windows = utils.search_windows(video, windows, svc, X_scaler,
                                       color_space=utils.COLORSPACE,
                                       spatial_size=utils.SPATIAL_SIZE,
                                       hist_bins=utils.HIST_BINS,
                                       orient=utils.ORIENT,
                                       pix_per_cell=utils.PX_PER_CELL,
                                       cell_per_block=utils.CELL_PER_BLOCK,
                                       hog_channel=utils.HOG_CHANNEL,
                                       spatial_feat=utils.SPATIAL_FEATURES,
                                       hist_feat=utils.HIST_FEATURES,
                                       hog_feat=utils.HOG_FEATURES)

    heat = np.zeros_like(video[:, :, 0]).astype(np.float)
    # Apply threshold to help remove false positives
    utils.add_heat(heat,hot_windows)
    # Visualize the heatmap when displaying
    heatmap = np.clip(heat, 0, 255)
    # Find final boxes from heatmap using label function
    d.append(heatmap)
    a = np.average(d,axis=0)

    av_thresh = utils.apply_threshold(a,2)
    labels = label(av_thresh)
    #draw hotspots on vid
    h = utils.draw_labeled_bboxes(np.copy(video), labels)
    #scale back up
    h = h.astype(np.float32) * 255
    return h


video_path = 'project_video.mp4'
video_output = 'project_result.mp4'
output = VideoFileClip(video_path)
input = output.fl_image(pipeline)
input.write_videofile(video_output, audio=False)

print('end')
#vehicle_data = vehicle_data[0:100]
# car = mpimg.imread(vehicle_data[0])
# img = (car*255).astype(np.uint8)
#
# x,s= hog(img[:,:,0], orientations=9, pixels_per_cell=(8, 8),
#                     cells_per_block=(2, 2), visualise=True)
# heatmap  = pipeline(image)
#
# image2 = mpimg.imread('/home/pierro/Work/udacity/self-driving-car/p5/test_images/test6.jpg')
# image2 = image2.astype(np.float32)/255
# draw_image2 = np.copy(image2)
# heatmap2  = pipeline(image2)
#
# plt.figure(figsize=(10,5))
# plt.subplot(1, 2, 1)
# plt.imshow(heatmap)
# plt.xlabel('figure 1')
#
# plt.subplot(1, 2, 2)
# plt.imshow(heatmap2)
# plt.xlabel('figure 2')
# plt.show(block=True)



