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

"""

import json
import boto3
import botocore
from datetime import datetime, timedelta, date

def check_ec2_instances(region):
    """
    ec2の['instances']が
    runningならその数を表示する

    Parameters
    ----------
    region : string
        AWSのリージョン情報

    returns
    -------
    res : [string]
        表示文章（サービスごとの稼働数のカウント結果）
    res2 : [string]
        表示文章（サービスごとの稼働数のカウント結果。0以上のみ）
    """
    client = boto3.Session().client(service_name="ec2", region_name=region)
    cnt = {'EC2 instances':0}
    res = []
    res2 = []
    try:
        running_instances = client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running']
                }
            ]
        )['Reservations']
        for reservation in running_instances:
            cnt[ 'EC2 instances' ] += 1
        for k,v in cnt.items():
            res.append('Running Ec2 {} : {}'.format(k,v))
            if v > 0:
                res2.append('Running Ec2 {} : {}'.format(k,v))
    except botocore.exceptions.ClientError as e:
        res.append('region-error in {} about {}'.format(region, 'ec2'))
        # print(e)
    return res, res2
    
def check_sagemaker_studios(region):
    """
    sagemaker studioの['KernelGateway', 'JupyterServer']が
    InServiceならその数を表示する

    Parameters
    ----------
    region : string
        AWSのリージョン情報

    returns
    -------
    res : [string]
        表示文章（サービスごとの稼働数のカウント結果）
    res2 : [string]
        表示文章（サービスごとの稼働数のカウント結果。0以上のみ）
    """
    client = boto3.Session().client(service_name="sagemaker", region_name=region)
    cnt = {'KernelGateway':0, 'JupyterServer':0}
    res = []
    res2 = []
    try:
        for app in client.list_apps()['Apps']:
            if app['Status']=='InService' and app['AppType'] in ['KernelGateway', 'JupyterServer']:
                cnt[ app['AppType'] ] += 1
        for k,v in cnt.items():
            res.append('InService sagemaker {} : {}'.format(k,v))
            if v > 0:
                res2.append('InService sagemaker {} : {}'.format(k,v))
    except botocore.exceptions.ClientError as e:
        res.append('region-error in {} about {}'.format(region, 'sagemaker studio'))
        # print(e)
    return res, res2
    

def check_sagemaker_endpoints(region):
    """
    sagemaker studioのendpointが
    InServiceならその数を表示する

    Parameters
    ----------
    region : string
        AWSのリージョン情報

    returns
    -------
    res : [string]
        表示文章（サービスごとの稼働数のカウント結果）
    res2 : [string]
        表示文章（サービスごとの稼働数のカウント結果。0以上のみ）
    """
    client = boto3.Session().client(service_name="sagemaker", region_name=region)
    res = []
    res2 = []
    try:
        ep_list = client.list_endpoints(
                    StatusEquals='InService'
                )['Endpoints']
        res.append('InService sagemaker endpoints : {}'.format(len(ep_list)))
        if len(ep_list) > 0:
            res2.append('InService sagemaker endpoints : {}'.format(len(ep_list)))
    except botocore.exceptions.ClientError as e:
        res.append('region-error in {} about {}'.format(region, 'sagemaker endpoint'))
    return res, res2

def check_comprehend_endpoints(region):
    """
    comprehendのendpointが
    IN_SERVICEならその数を表示する

    Parameters
    ----------
    region : string
        AWSのリージョン情報
    
    returns
    -------
    res : [string]
        表示文章（サービスごとの稼働数のカウント結果）
    res2 : [string]
        表示文章（サービスごとの稼働数のカウント結果。0以上のみ）
    """
    client = boto3.Session().client(service_name="comprehend", region_name=region)
    res = []
    res2 = []
    cnt = 0
    try:
        for ep in client.list_endpoints()['EndpointPropertiesList']:
            if ep['Status'] == 'IN_SERVICE':
                cnt += 1
        res.append('IN_SERVICE comprehend endpoints : {}'.format(cnt))
        if cnt > 0:
            res2.append('IN_SERVICE comprehend endpoints : {}'.format(cnt))
    except botocore.exceptions.ClientError as e:
        res.append('region-error in {} about {}'.format(region, 'comprehend endpoint'))
    return res, res2

def check_redshift_clusters(region):
    """
    redshiftのclusterが
    ['deleting', 'paused']以外ならその数を表示する

    Parameters
    ----------
    region : string
        AWSのリージョン情報
    
    returns
    -------
    res : [string]
        表示文章（サービスごとの稼働数のカウント結果）
    res2 : [string]
        表示文章（サービスごとの稼働数のカウント結果。0以上のみ）
    """
    client = boto3.Session().client(service_name="redshift", region_name=region)
    res = []
    res2 = []
    cnt = 0
    try:
        for clu in client.describe_clusters()['Clusters']:
            if not clu['ClusterStatus'] in ['deleting', 'paused']:
                cnt += 1
        res.append('active redshift endpoints : {}'.format(cnt))
        if cnt > 0:
            res2.append('active redshift endpoints : {}'.format(cnt))
    except botocore.exceptions.ClientError as e:
        res.append('region-error in {} about {}'.format(region, 'redshift cluster'))
    return res, res2

def check_resources():
    """
    サービスチェック関数を全リージョンについて実行する
    """
    region_result = dict()
    region_result2 = dict()

    # sagemaker
    regions = boto3.Session().get_available_regions('sagemaker')
    # regions = ['eu-west-2']
    for region in regions:
        if not region in region_result:
            region_result[region] = []
        if not region in region_result2:
            region_result2[region] = []
        res, res2 = check_sagemaker_endpoints(region)
        region_result[region] += res
        region_result2[region] += res2
        res, res2 = check_sagemaker_studios(region)
        region_result[region] += res
        region_result2[region] += res2
        
    # redshift
    regions = boto3.Session().get_available_regions('redshift')
    # regions = ['eu-west-2']
    for region in regions:
        if not region in region_result:
            region_result[region] = []
        if not region in region_result2:
            region_result2[region] = []
        res, res2 = check_redshift_clusters(region)
        region_result[region] += res
        region_result2[region] += res2
        
    # comprehend
    regions = boto3.Session().get_available_regions('comprehend')
    # regions = ['eu-west-2']
    for region in regions:
        if not region in region_result:
            region_result[region] = []
        if not region in region_result2:
            region_result2[region] = []
        res, res2 = check_comprehend_endpoints(region)
        region_result[region] += res
        region_result2[region] += res2
        
    # comprehend
    regions = boto3.Session().get_available_regions('ec2')
    # regions = ['eu-west-2']
    for region in regions:
        if not region in region_result:
            region_result[region] = []
        if not region in region_result2:
            region_result2[region] = []
        res, res2 = check_ec2_instances(region)
        region_result[region] += res
        region_result2[region] += res2
        
    res = []
    for k,v in region_result2.items():
        if len(v) > 0: 
            res.append(k)
            res += v
            res.append('====')
    
    print(*res, sep='\n')

def check_cost(region):
    client = boto3.client('ce')

    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': date.today().replace(day=1).isoformat(),
            'End': date.today().isoformat()
        },
        Granularity='MONTHLY',
        Metrics=[
            'AmortizedCost'
        ]
    )
    
    return response['ResultsByTime'][0]['Total']['AmortizedCost']['Amount']
    
def lambda_handler(event, context):
    """
    lambdaが参照する関数
    （lambda_handler(event, context)の形で設定する必要がある）
    check_resources()を実行するだけ
    """
    check_resources()
    print(check_cost('eu-west-2'))
    print('all done')
    return {
        'statusCode': 200,
        'body': json.dumps('Success!')
    }
