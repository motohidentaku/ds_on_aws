"""
AWS lambdaで必要なタイミングで実行することで、
設定したサービスの稼働状況を確認するためのスクリプトです。
利用するには下記＜設定項目＞の対応が必要となります。

＜設定項目＞
■初期設定
・タイムアウト時間の延長（10分あれば十分？）

■更新時設定（初期にも必要）
・AWS lambdaのコード更新
・role権限の更新

＜確認対象サービス＞
・SageMakerStudio（JupyterServer, KernelGateway）
・SageMakerEndpoint
・RedshiftCluster
・ComprehendEndpoint

＜roleに設定すべきポリシー＞
・AWSLambdaBasicExecutionRole
・AmazonSageMakerFullAccess
・AmazonRedshiftFullAccess
・ComprehendFullAccess
・AmazonEC2FullAccess


"""

import json
import boto3
import botocore

def get_ec2_instances_info():
    """
    全リージョンに対してEC2の稼働状況を取得する
    
    returns
    -------
    region_result : [string]
        インスタンの稼働状況
    """

    ret = []

    # OptInしないと使えないリージョン
    optout_regions = ['af-south-1', 'ap-east-1', 'eu-south-1', 'me-south-1']
    # 指定サービスのregionを取得
    regions = boto3.Session().get_available_regions('ec2')

    # OptInしないと使えないリージョンを除いて検索を実施
    for region in [i for i in regions if i not in optout_regions]:
        # if not region in region_result:
        #     region_result[region] = []

        client = boto3.Session().client(service_name='ec2', region_name=region)
        try:
            running_instances = client.describe_instances(
                Filters=[
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running']
                    }
                ]
            )['Reservations']

            for ec2_reservation in running_instances:
                for ec2_instance in ec2_reservation['Instances']:
                    ec2_instance_id = ec2_instance['InstanceId']
                    ec2_instance_type = ec2_instance['InstanceType']
                    
                    ret.append('region : {}, InstanceId : {}, InstanceType : {}'.format(region, ec2_instance_id, ec2_instance_type))
            
        except botocore.exceptions.ClientError as e:
            print('region-error in {} about {}'.format(region, service_name_text))


    return ret


def check_ec2_instances(client):
    """
    ec2の['instances']のうち
    runningの数を返す

    Parameters
    ----------
    client :  boto3.Session().client
        適切な権限の付与された　service_name="ec2"　のclient

    returns
    -------
    res : int
        サービスごとの稼働数のカウント結果
    """

    running_instances = client.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]
    )['Reservations']

    return len(running_instances)



def check_sagemaker_studios_kernel_gateway(client):
    """
    sagemaker studioの['KernelGateway']が
    InServiceならその数を表示する

    Parameters
    ----------
    client :  boto3.Session().client
        適切な権限の付与された　service_name="sagemaker"　のclient

    returns
    -------
    cnt : int
        サービスごとの稼働数のカウント結果
    """
    cnt = 0

    for app in client.list_apps()['Apps']:
        if app['Status']=='InService' and app['AppType'] in ['KernelGateway']:
            cnt += 1

    return cnt


def check_sagemaker_studios_jupyter_server(client):
    """
    sagemaker studioの['JupyterServer']が
    InServiceならその数を表示する

    Parameters
    ----------
    client :  boto3.Session().client
        適切な権限の付与された　service_name="sagemaker"　のclient

    returns
    -------
    cnt : int
        サービスごとの稼働数のカウント結果
    """
    cnt = 0

    for app in client.list_apps()['Apps']:
        if app['Status']=='InService' and app['AppType'] in ['JupyterServer']:
            cnt += 1

    return cnt


def check_sagemaker_endpoints(client):
    """
    sagemaker studioのendpointが
    InServiceならその数を返す

    Parameters
    ----------
    client :  boto3.Session().client
        適切な権限の付与された　service_name="sagemaker"　のclient

    returns
    -------
    res : int
        サービスごとの稼働数のカウント結果
    """
    
    ep_list = client.list_endpoints(
                StatusEquals='InService'
            )['Endpoints']

    return len(ep_list)

def check_comprehend_endpoints(client):
    """
    comprehendのendpointが
    IN_SERVICEならその数を表示する

    Parameters
    ----------
    client :  boto3.Session().client
        適切な権限の付与された　service_name="comprehend"　のclient
    
    returns
    -------
    res : int
        サービスごとの稼働数のカウント結果
    """

    cnt = 0
    for ep in client.list_endpoints()['EndpointPropertiesList']:
        if ep['Status'] == 'IN_SERVICE':
            cnt += 1

    return cnt

def check_redshift_clusters(client):
    """
    redshiftのclusterが
    ['deleting', 'paused']以外ならその数を表示する

    Parameters
    ----------
    client :  boto3.Session().client
        適切な権限の付与された　service_name="redshift"　のclient
    
    returns
    -------
    res : int
        サービスごとの稼働数のカウント結果
    """

    cnt = 0
    
    for clu in client.describe_clusters()['Clusters']:
        if not clu['ClusterStatus'] in ['deleting', 'paused']:
            cnt += 1
        
    return cnt


def check_resources(service_name, service_name_text, func):
    """
    指定サービスの全リージョンに対してサービス稼働数を取得する

    Parameters
    ----------
    service_name : string
        AWSのサービス名　boto3.Session().clientのservice_nameに引き渡す
    service_name_text : string
        文字列を出力するときのサービス名
    func : string
        service実行件数を取得するための関数名
    
    returns
    -------
    region_result : dict()
        サービスごとの稼働数のカウント結果
        [region][service_name_text]
    """

    region_result = dict()

    # OptInしないと使えないリージョン
    optout_regions = ['af-south-1', 'ap-east-1', 'eu-south-1', 'me-south-1']
    # 指定サービスのregionを取得
    regions = boto3.Session().get_available_regions(service_name)

    # OptInしないと使えないリージョンを除いて検索を実施
    for region in [i for i in regions if i not in optout_regions]:
        if not region in region_result:
            region_result[region] = dict()

        client = boto3.Session().client(service_name=service_name, region_name=region)
        try:
            region_result[region][service_name_text] = func(client)
            
        except botocore.exceptions.ClientError as e:
            print('region-error in {} about {}'.format(region, service_name_text))


    return region_result

def deepupdate(dict_base, other):
  for k, v in other.items():
    if isinstance(v, dict) and k in dict_base:
      deepupdate(dict_base[k], v)
    else:
      dict_base[k] = v

def check_all_resources():
    """
    サービスチェック関数を全リージョンについて実行する
    """
    region_result = dict()
    
    # sagemaker
    deepupdate(region_result, check_resources('sagemaker', 'sagemaker_kernel_gateway', check_sagemaker_studios_kernel_gateway))
    deepupdate(region_result, check_resources('sagemaker', 'sagemaker_jupyter_server', check_sagemaker_studios_jupyter_server))
    # redshift
    deepupdate(region_result, check_resources('redshift', 'redshift_clusters', check_redshift_clusters))
    # redshift
    deepupdate(region_result, check_resources('comprehend', 'comprehend_endpoints', check_comprehend_endpoints))
    # ec2
    deepupdate(region_result, check_resources('ec2', 'ec2 instances', check_ec2_instances))

    # 出力
    res = []
    print_flag = False
    for region, v in region_result.items():
        for service, cnt in v.items():
            if cnt > 0: 
                if not False:
                    res.append('region: {}'.format(region))
                res.append('  {} : {}'.format(service, cnt))
                print_flag = True
        if print_flag:
            res.append('====')
            print_flag = False
    
    print(*res, sep='\n')
    
    
def lambda_handler(event, context):
    """
    lambdaが参照する関数
    （lambda_handler(event, context)の形で設定する必要がある）
    check_resources()を実行するだけ
    """
    check_all_resources()
    print(*get_ec2_instances_info(), sep='\n')
    print('all done')
    return {
        'statusCode': 200,
        'body': json.dumps('Success!')
    }

if __name__ == '__main__':
    check_all_resources()
