part def PointCloudFilter :> PerceptionPipeline {
    :>> nodeName = "pointcloud_filter";
    :>> namespace = "/perception";
    port :>> rawSub : TopicSubscriber {
        :>> topicName = "/depth/image";
        in item :>> msg : Image;
    }
    port :>> processedPub : TopicPublisher {
        :>> topicName = "/filtered_cloud";
        out item :>> msg : PointCloud2;
    }
    attribute voxelSize : DeclaredParameter {
        :>> name = "voxel_size";
        :>> parameterType = ParameterTypeKind::Double;
    }
}
