const awsConfig = {
  aws_project_region: process.env.AWS_REGION,
  aws_cognito_region: process.env.AWS_REGION,
  aws_user_pools_id: process.env.WS_USER_POOL_ID,
  aws_user_pools_web_client_id: process.env.WS_USER_POOL_CLIENT_ID,
};

export default awsConfig;