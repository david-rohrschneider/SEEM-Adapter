# --------------------------------------------------------
# X-Decoder -- Generalized Decoding for Pixel, Image, and Language
# Copyright (c) 2022 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Modified by Xueyan Zou (xueyan@cs.wisc.edu)
# --------------------------------------------------------

import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)
import os
import sys
import torch
import logging
import wandb
import dotenv

from utils.arguments import load_opt_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv.load_dotenv(".env")

def init_wandb(args, job_dir, project, job_name='tmp'):
    wandb_dir = os.path.join(job_dir, 'wandb')
    os.makedirs(wandb_dir, exist_ok=True)
    runid = None
    if os.path.exists(f"{wandb_dir}/runid.txt"):
        runid = open(f"{wandb_dir}/runid.txt").read()

    wandb.init(project=project,
            name=job_name,
            dir=wandb_dir,
            entity=os.environ['WANDB_ENTITY'],
            resume="allow",
            id=runid,
            config={"hierarchical": True},)

    open(f"{wandb_dir}/runid.txt", 'w').write(wandb.run.id)
    wandb.config.update({k: args[k] for k in args if k not in wandb.config})

def main(args=None):
    '''
    [Main function for the entry point]
    1. Set environment variables for distributed training.
    2. Load the config file and set up the trainer.
    '''

    opt, cmdline_args = load_opt_command(args)
    command = cmdline_args.command

    if cmdline_args.user_dir:
        absolute_user_dir = os.path.abspath(cmdline_args.user_dir)
        opt['base_path'] = absolute_user_dir

    # update_opt(opt, command)
    world_size = 1
    if 'OMPI_COMM_WORLD_SIZE' in os.environ:
        world_size = int(os.environ['OMPI_COMM_WORLD_SIZE'])

    if opt['TRAINER'] == 'xdecoder':
        from trainer import XDecoder_Trainer as Trainer
    else:
        assert False, "The trainer type: {} is not defined!".format(opt['TRAINER'])
    
    trainer = Trainer(opt)
    os.environ['TORCH_DISTRIBUTED_DEBUG']='DETAIL'

    if command == "train":
        if opt['rank'] == 0 and opt['WANDB']:
            wandb.login(key=os.environ['WANDB_KEY'])
            init_wandb(
                args=opt,
                job_dir=trainer.save_folder,
                job_name=f"{opt['WANDB_EXP_NAME']}__{trainer.save_folder.split('/')[-1]}",
                project=os.environ['WANDB_PROJECT']
            )
        trainer.train()
    elif command == "evaluate":
        trainer.eval()
    else:
        raise ValueError(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
    sys.exit(0)
