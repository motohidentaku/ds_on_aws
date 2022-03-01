"""
AWS lambdaで日次バッチ的に利用することで、
設定したサービスを自動停止するためのスクリプトです。
利用するには下記＜設定項目＞の対応が必要となります。

＜設定項目＞
■初期設定
・EventBridgeによる定期実行の設定
・タイムアウト時間の延長（3分ぐらいでOK？）

■更新時設定（初期にも必要）
・AWS lambdaのコード更新
・role権限の更新

＜自動停止の対象サービス＞
・SageMakerStudio（JupyterServer, KernelGateway）
・SageMakerEndpoint
・RedshiftCluster
・ComprehendEndpoint

＜roleに設定すべきポリシー＞
・AWSLambdaBasicExecutionRole
・AmazonSageMakerFullAccess
・AmazonRedshiftFullAccess
・ComprehendFullAccess


＜残課題＞
・ログの出力
・タグによる自動停止の回避
→　（Tag,Key）＝（'AutoAtop','False'）で止めないようにしようと考えているが、
　　うまく動いているかは不明。
　　sagemakerはたぶん動いている。
"""

import json
import boto3
import botocore

def delete_sagemaker_studios(region):
    """
    sagemaker studioの['KernelGateway', 'JupyterServer']が
    InServiceなら削除する

    Parameters
    ----------
    region : string
        AWSのリージョン情報
    """
    client = boto3.Session().client(service_name="sagemaker", region_name=region)
    try:
        for app in client.list_apps()['Apps']:
            if app['Status']=='InService' and app['AppType'] in ['KernelGateway', 'JupyterServer']:
                stop_resource = True
                desc = client.describe_app(
                        DomainId = app['DomainId'],
                        UserProfileName = app['UserProfileName'],
                        AppType = app['AppType'],
                        AppName = app['AppName']
                    )
                tags = client.list_tags(
                    ResourceArn=desc['AppArn']
                )['Tags']
                for tag in tags:
                    if tag['Key'] == 'AutoStop' and tag['Value'] == 'False':
                        stop_resource = False
                
                if stop_resource:
                    res = client.delete_app(
                        DomainId = app['DomainId'],
                        UserProfileName = app['UserProfileName'],
                        AppType = app['AppType'],
                        AppName = app['AppName']
                    )
    except botocore.exceptions.ClientError as e:
        print('region-error')

def delete_sagemaker_endpoints(region):
    """
    sagemaker studioのendpointが
    InServiceなら削除する

    Parameters
    ----------
    region : string
        AWSのリージョン情報
    """
    client = boto3.Session().client(service_name="sagemaker", region_name=region)
    try:
        ep_list = client.list_endpoints(
                    StatusEquals='InService'
                )['Endpoints']
        for ep in ep_list:
            stop_resource = True
            tags = client.list_tags(
                ResourceArn=ep['EndpointArn']
            )['Tags']
            for tag in tags:
                if tag['Key'] == 'AutoStop' and tag['Value'] == 'False':
                    stop_resource = False
            
            if stop_resource:
                res = client.delete_endpoint(
                    EndpointName = ep['EndpointName']
                )
    except botocore.exceptions.ClientError as e:
        print('region-error')

def delete_comprehend_endpoints(region):
    """
    comprehendのendpointが
    IN_SERVICEなら削除する

    Parameters
    ----------
    region : string
        AWSのリージョン情報
    """
    client = boto3.Session().client(service_name="comprehend", region_name=region)
    try:
        for ep in client.list_endpoints()['EndpointPropertiesList']:
            if ep['Status'] == 'IN_SERVICE':
                stop_resource = True
                # tagの取得がうまく働いているか不明なので、現状は全てのエンドポイントを停止していると思ったほうが良い
                try:
                    tags = client.list_tags_for_resource(
                        ResourceArn=ep['EndpointArn']
                    )['Tags']

                    if tags['AutoStop'] == 'False':
                        stop_resource = False
                except:
                    pass

                if stop_resource:
                    response = client.delete_endpoint(
                        EndpointArn= ep['EndpointArn']
                    )
                    print(response)
    except botocore.exceptions.ClientError as e:
        print('region-error')

def pause_redshift_clusters(region):
    """
    redshiftのclusterが
    ['deleting', 'paused']以外なら停止（'paused'）する

    Parameters
    ----------
    region : string
        AWSのリージョン情報
    """
    client = boto3.Session().client(service_name="redshift", region_name=region)
    try:
        for clu in client.describe_clusters()['Clusters']:
            if not clu['ClusterStatus'] in ['deleting', 'paused']:
                stop_resource = True
                # tagの取得がうまくいかないので、現状は全てのクラスターを停止
#                 try:
#                     tags = client.describe_tags(
#                         ResourceName=clu['ClusterNamespaceArn'],
#                         ResourceType='Cluster',
#                     )['TaggedResources'][0]['Tag']
                    
#                     for tag in tags:
#                         if tag['Key'] == 'AutoStop' and tag['Value'] == 'False':
#                                 stop_resource = False
                        
#                     if tags['AutoStop'] == 'False':
#                         stop_resource = False
#                 except:
#                     pass
                
                if stop_resource:
                    response = client.pause_cluster(
                        ClusterIdentifier= clu['ClusterIdentifier']
                    )
                    print(response)
    except botocore.exceptions.ClientError as e:
        print('region-error') 

def stop_resources():
    """
    サービス停止関数を全リージョンについて実行する
    """
    # sagemaker
    regions = boto3.Session().get_available_regions('sagemaker')
    # regions = ['eu-west-2']
    for region in regions:
        delete_sagemaker_endpoints(region)
        delete_sagemaker_studios(region)
        
    # redshift
    regions = boto3.Session().get_available_regions('redshift')
    # regions = ['eu-west-2']
    for region in regions:
        pause_redshift_clusters(region)
    
    # comprehend
    regions = boto3.Session().get_available_regions('comprehend')
    # regions = ['eu-west-2']
    for region in regions:
        delete_comprehend_endpoints(region)

def lambda_handler(event, context):
    """
    lambdaが参照する関数
    （lambda_handler(event, context)の形で設定する必要がある）
    stop_resources()を実行するだけ
    """
    stop_resources()
    return {
        'statusCode': 200,
        'body': json.dumps('Success!')
    }